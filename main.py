import os, django

import email_logic

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pysite.settings')
django.setup()

# Everything else must start here

import json5
from asgiref.sync import sync_to_async
from django.conf import settings

from website.models import ChatSession, Prompt


import uuid
import sys
import re
import ast
import aiohttp
import mistune
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Request
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware

from flowster import FlowSheet, FlowProfile, flowster_node, FlowExclude, \
    FlowsterChunk
from flowster.stdlib import media
from flowster.stdlib.ai.llm import chat_stream, chat_result, list_models
import asyncio
import json
import requests
from datetime import datetime
import regex as re

from flowster.stdlib.storage import cache, filesystem
from settings import FLOW_SHEET, SKIP

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_dicts_from_text(text: str):
    pattern = r'''
        \{                          # opening brace
            (?:                     # non‑capturing group
                [^{}"']+            # anything but braces or quotes
              | "(?:\\.|[^"\\])*"   # double‑quoted string
              | '(?:\\.|[^'\\])*'   # single‑quoted string
              | (?R)                # recursive reference
            )*
        \}                          # closing brace
    '''

    try:
        raw_dicts = re.findall(pattern, text, flags=re.VERBOSE | re.DOTALL)
        return [json5.loads(d) for d in raw_dicts]

    except Exception as e:
        print("Error parsing JSON5:", e)
        return []

async def stream_safe( js:dict, bs=32768 ):
    s = json.dumps(js)
    if len(s) <= bs:
        yield f"data: {s}\n\n"
        return

    for i in range(0, len(s), bs):
        payload = {"data": s[i:i+bs], "is_start": i == 0, "is_done": i + bs >= len(s)}
        yield f"partial: {json.dumps(payload)}\n\n"


async def sse_stream( stream, conversation, callback=None ):
    if callback is None:
        async def callback( chunk ):
            pass

    bs = 4096  # Stream in 4KB chunks
    async for chunk in stream:
        # Run the callback
        if (cb_data := await callback(chunk)):
            async for packet in stream_safe(cb_data, bs):
                yield packet

        if chunk.type == 'content':
            js = {"type": "content", "text": chunk.text}

        elif chunk.type == 'thinking':
            js = {"type": "thinking", "text": chunk.text}

        elif chunk.type == 'conversation':
            conversation.append( chunk.metadata )
            continue

        else:
            continue

        # Stream safely
        async for packet in stream_safe( js, bs ):
            yield packet

    # Finally send the full conversation
    js = {"type": "conversation", "conversation": conversation}
    async for packet in stream_safe(js, bs):
        yield packet

    # Run the final callback
    if (cb_data := await callback( None )):
        async for packet in stream_safe(cb_data, bs):
            yield packet


def context_to_kwargs( contexts: list[dict] ):
    kwargs = {}
    for ctx in contexts:
        if not all(k in ctx for k in ('name', 'content')):
            continue
        name, content = ctx['name'], ctx['content']

        if name.lower() == 'system':
            kwargs['system'] = content
        else:
            if 'contexts' not in kwargs:
                kwargs['contexts'] = {}
            kwargs['contexts'][name] = content
    return kwargs


# Helper to concatenate all text children of a node
def text_from_children(node: Dict[str, Any]) -> str:
    return "".join(
        child["raw"] for child in node.get("children", []) if
        child["type"] == "text"
    )

def parse_variables(text: str):
    BRACE = re.compile(r'\{([^}]+)\}')
    BRACKET = re.compile(r'\[([^\]]+)\]')
    NAME = re.compile(r'([^:]+):')
    PAREN = re.compile(r'\(([^\)]+)\)')

    if not (m := NAME.search(text)):
        return None

    desc = re.sub(r'^[^:]*:', '', text).strip()
    label = m.group(1).strip().capitalize()
    name = label.lower().replace(' ', '_')
    col_span, col_end, data_type, flags = 6, 0, 'string', []
    if (m := BRACE.search(text)):
        desc = desc.replace(m.group(0), '')
        props = m.group(1).split(',')
        col_span = props[0].strip() if len(props) > 0 else 6
        col_end = props[1].strip() if len(props) > 1 else 0
    if (m := BRACKET.search(text)):
        desc = desc.replace(m.group(0), '')
        data_type = m.group(1).strip()
    if (m := PAREN.search(text)):
        desc = desc.replace(m.group(0), '')
        flags = [f.strip() for f in m.group(1).split(',')]

    return {'name': name, 'label': label, 'col_span': col_span, 'col_end': col_end,
            'data_type': data_type, 'flags': flags, 'description': desc.strip()}


@app.post("/api/configure_section")
async def configure_section(request:Request):
    body = await request.json()
    md_text: str = body.get('markdown', '')

    # 1. Create a Mistune instance that returns an AST
    md = mistune.create_markdown(renderer="ast")
    ast = md(md_text)  # → list of node dicts

    features: List[Dict[str, Any]] = []

    title = None
    intro = None
    structure = []

    # Parse the data into "features"
    for node in ast:
        node_type = node["type"]

        if node_type == "heading":
            title = text_from_children(node)
            features.append(
                {
                    "type": "heading",
                    "level": node["attrs"]["level"],
                    "text": text_from_children(node),
                }
            )

        elif node_type == "paragraph":
            intro = text_from_children(node)
            features.append(
                {
                    "type": "paragraph",
                    "text": text_from_children(node),
                }
            )

        elif node_type == "list":
            # Each child of a list is a list_item
            items = []
            for li in node.get("children", []):
                # A list_item contains a paragraph (or several paragraphs)
                # Grab all text from that paragraph
                for child in li.get("children", []):
                    if child["type"] == "paragraph" or child["type"] == "block_text":
                        if (vars := parse_variables(text_from_children(child))):
                            structure.append( vars )
                        items.append(text_from_children(child))
            features.append(
                {
                    "type": "list",
                    "ordered": node["attrs"]["ordered"],
                    "items": items,
                }
            )

    return {
        "features": features,
        "title": title,
        "intro": intro,
        "structure": structure,
        'successful': True
    }


@app.post("/api/chat")
async def chat(request:Request):#question: str=Body(...), conversation: list[dict]=Body(...)):
    body = await request.json()
    chat_session_uid: str = body.get('chat_session_uid', None)
    question: str = body.get('question', '')
    conversation: list[dict] = body.get('conversation', [])
    contexts: list[dict] = body.get('contexts', [])
    model: str = body.get('model', None)

    # Get or create the chat session
    chat_sess = await ChatSession.getByUid(chat_session_uid)
    if chat_sess and chat_sess.suggested_consultation:
        return await profile_chat(request)
    else:
        return await knowledge_chat(request)


async def knowledge_chat(request:Request):#question: str=Body(...), conversation: list[dict]=Body(...)):
    body = await request.json()
    chat_session_uid: str = body.get('chat_session_uid', None)
    question: str = body.get('question', '')
    conversation: list[dict] = body.get('conversation', [])
    contexts: list[dict] = body.get('contexts', [])
    model: str = body.get('model', None)

    images = [x['content'] for x in contexts if x['file_type'] == 'image']
    contexts = [x for x in contexts if x['file_type'] != 'image']

    # Add variable params
    kwargs = context_to_kwargs( contexts )

    kwargs['system'] = """
    You are a helpful AI assistant.
    Use the provided KNOWLEDGE_BASE to answer the user's question as best as you can. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    If the user asks to setup a consultation or meeting, respond with "Let's get started by getting your **name** and a **description** of your needs."
    """

    # Suggest scheduling a consultation?
    if len(conversation) > 2:
        kwargs['system'] += "\nAfter answering the user's question, suggest scheduling a free consultation by saying."

    if 'contexts' not in kwargs:
        kwargs['contexts'] = {}
    with open("knowledge_base.md", "r") as f:
        kwargs['contexts']['KNOWLEDGE_BASE'] = f.read()

    # Store the model if its changed
    if model is not None and model != "":
        await filesystem.write(FLOW_SHEET, f"model", model)

    # Get or create the chat session
    chat_sess = await ChatSession.getOrCreateByUid(chat_session_uid, question[:64] )

    # Add the user's question
    await Prompt.create( type=Prompt.TYPE_USER, chat_session=chat_sess, content=question )

    # Endpoint that returns a single response
    if (_stream := await chat_stream(
        FLOW_SHEET,
        question,
        conversation=conversation,
        tools=[],
        images=images,
        model=model,
        **kwargs
    )).is_err():
        return {"error": _stream.err_value}
    stream = _stream.ok_value

    # Create the streamer
    if (ret := await chat_result( FLOW_SHEET, stream )).is_err():
        return {"error": ret.err_value}

    # Create my system prompt
    assistant = Prompt(chat_session=chat_sess, type=Prompt.TYPE_ASSISTANT)

    async def save_chat( chunk ):
        if chunk is None: # Finished
            await sync_to_async(assistant.save)()
            return {'type': 'chat_session', 'chat_session_uid': str(chat_sess.uid)}

        elif chunk.type == 'full_content':
            assistant.content = chunk.text
            safe_text = re.sub(r'[^a-zA-Z ]', '', chunk.text.lower())
            if re.search('lets get started by getting', safe_text, re.IGNORECASE):
                chat_sess.suggested_consultation = True
                await sync_to_async(chat_sess.save)()

        elif chunk.type == 'full_thinking':
            assistant.thinking = chunk.text


    """Endpoint that streams events using SSE"""
    return StreamingResponse(
        sse_stream( ret.ok_value, conversation, save_chat ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )



async def profile_chat(request:Request):#question: str=Body(...), conversation: list[dict]=Body(...)):
    body = await request.json()
    question: str = body.get('question', '')
    conversation: list[dict] = body.get('conversation', [])
    contexts: list[dict] = body.get('contexts', [])
    model: str = body.get('model', None)
    chat_session_uid: str = body.get('chat_session_uid', None)

    # Get or create the chat session
    chat_sess = await ChatSession.getOrCreateByUid(chat_session_uid, question[:64] )

    if len([x for x in contexts if x.get('name') == 'system']) <= 0:
        contexts.append({
            'name': 'system',
            'content': '''Based on STRUCTURE, update PROFILE. Only output JSON data.''',
            'file_type': 'text',
        })


    if len([x for x in contexts if x.get('name') == 'system_text']) <= 0:
        system_text = {
            'name': 'system_text',
            'content': '''
            Request for the missing data from PROFILE based on STRUCTURE. 
            Be friendly and concise. 
            Always respond in full sentences, not JSON. 
            If everything is complete, respond with "Your meeting has been scheduled." repeating back the details.
            ''',
            'file_type': 'text',
        }
    else:
        system_text = [x for x in contexts if x.get('name') == 'system_text'][0]
        contexts = [x for x in contexts if x.get('name') != 'system_text']

    images = [x['content'] for x in contexts if x['file_type'] == 'image']
    contexts = [x for x in contexts if x['file_type'] != 'image']

    # Add variable params
    kwargs = context_to_kwargs( contexts )

    if 'contexts' not in kwargs:
        kwargs['contexts'] = {}
    structure = {
        "name": "Full Name",
        "email": "Email Address",
        "phone": "Phone Number",
        "description": "Description of the job or needs. Its okay to add more details here as they are provided.",
        "budget": "Estimated Budget (if known)",
        "timeline": "Preferred Timeline for starting the project",
        "date_time": "Preferred **Date and Time** for the consultation",
    }
    kwargs['contexts']['STRUCTURE'] = json.dumps(structure, indent=4)

    # Store the model if its changed
    if model is not None and model != "":
        await filesystem.write(FLOW_SHEET, f"model", model)

    async def _sse_stream():
        # Data only

        # Add the user's question
        await Prompt.create(type=Prompt.TYPE_USER, chat_session=chat_sess, content=question)

        # Endpoint that returns a single response
        if (_stream := await chat_stream(
            FLOW_SHEET,
            question,
            conversation=[],
            tools=[],
            images=images,
            model=model,
            **kwargs
        )).is_err():
            yield f'error: {_stream.err_value}\n\n'
            return
        data_stream = _stream.ok_value

        # Create the streamer
        if (data_only := await chat_result( FLOW_SHEET, data_stream )).is_err():
            yield f'error: {data_only.err_value}\n\n'
            return

        # Create my system prompt
        assistant = Prompt(chat_session=chat_sess, type=Prompt.TYPE_ASSISTANT)
        assistant.extra = {
            'raw': None,
            'before': None,
            'after': None,
            'thinking': None,
        }

        async for chunk in data_only.ok_value:
            if chunk.type == 'full_thinking':
                assistant.extra['thinking'] = chunk.text

            elif chunk.type == 'full_content':
                target = kwargs['contexts']['PROFILE']
                assistant.extra['raw'] = chunk.text
                assistant.extra['before'] = target

                # Conver to dict
                try:
                    target = json5.loads(target)
                except:
                    target = {}
                if target is None or target == '' or not isinstance(target, dict):
                    target = {}

                # Extract profiles from the text
                profiles = extract_dicts_from_text(chunk.text)
                for profile in profiles:
                    for key in structure.keys():
                        if isinstance(profile[key], str) and profile[key]:
                            target[key] = profile[key].strip()

                # Save the table info
                assistant.extra['after'] = target
                await sync_to_async(assistant.save)()

                chat_sess.profile = target
                await sync_to_async(chat_sess.save)()

                js = {"type": "profile", "profile": target}
                yield f"data: {json.dumps(js)}\n\n"

                # Store the updated profile!
                kwargs['contexts']['PROFILE'] = json5.dumps(target)

        # Human response
        kwargs['system'] = system_text['content']

        # Endpoint that returns a single response
        if (_stream := await chat_stream(
            FLOW_SHEET,
            question,
            conversation=conversation,
            tools=[],
            images=images,
            model=model,
            **kwargs
        )).is_err():
            yield f"error: {_stream.err_value}\n\n"
            return
        stream = _stream.ok_value

        # Create the streamer
        if (stream_ret := await chat_result( FLOW_SHEET, stream )).is_err():
            yield f"error: {stream_ret.err_value}\n\n"
            return

        bs = 4096
        async for chunk in stream_ret.ok_value:
            if chunk.type == 'content':
                js = {"type": "content", "text": chunk.text}

            elif chunk.type == 'thinking':
                js = {"type": "thinking", "text": chunk.text}

            elif chunk.type == 'conversation':
                conversation.append(chunk.metadata)
                continue

            elif chunk.type == 'full_thinking':
                assistant.thinking = chunk.text

            elif chunk.type == 'full_content':
                assistant.content = chunk.text
                await sync_to_async(assistant.save)()

                if re.search(r'your meeting has been scheduled', chunk.text, re.IGNORECASE):
                    info = json5.loads(kwargs['contexts']['PROFILE'])
                    email_logic.raw_email(info['email'], 'Mountain America Homes Consultation', f'A new consultation has been scheduled with the following details:\n\n{chunk.text}')

            else:
                continue

            # Stream safely
            async for packet in stream_safe(js, bs):
                yield packet

        # Finally send the full conversation
        js = {"type": "conversation", "conversation": conversation}
        async for packet in stream_safe(js, bs):
            yield packet

    """Endpoint that streams events using SSE"""
    return StreamingResponse(
        _sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/tags")
async def get_tags():
    if (_ret := await list_models(FLOW_SHEET)).is_err():
        return {"error": _ret.err_value}
    models = _ret.ok_value

    return {"models": models, 'successful': True}


@app.post("/api/model")
async def _model(request:Request):
    body = await request.json()
    model: str = body.get('model', None)

    if model is None or model == '':
        model = None
        if (_model := await filesystem.read(FLOW_SHEET, f"model")).is_ok():
            if _model.ok_value is not None and _model.ok_value != '':
                model = _model.ok_value

    else:
        if (ret := await filesystem.write(FLOW_SHEET, f"model", model)).is_err():
            return {"successful": False, "reason": ret.err_value}

    return {"successful": True, "model": model}


@app.get("/api/list_conversations")
async def list_conversations(request:Request):
    conversations = await sync_to_async( list )( ChatSession.objects.all().order_by('-timestamp_on'))
    return {"successful": True, "conversations": [x.toJson() for x in conversations]}


@app.post("/api/conversation")
async def list_conversations(request:Request):
    body = await request.json()
    conversation_uid = body.get('conversation_uid', None)

    conversation = await ChatSession.getByUid(conversation_uid)
    if conversation is None:
        return {"successful": False, "reason": "Conversation not found."}

    _prompts = Prompt.objects.filter(chat_session=conversation).order_by('id')
    prompts = [x.toJson() for x in await sync_to_async( list )( _prompts )]
    return {"successful": True, "conversation": conversation.toJson(), "prompts": prompts }


@app.websocket("/ws/speech_to_text")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    if SKIP.get('AUDIO_INPUT'):
        await websocket.send_json({"error": "Speech to text is disabled in settings."})
        await websocket.close()
        return

    try:
        async def read_audio():
            while True:
                yield await websocket.receive_bytes()

        # Setup teh audio to text
        if (ret := await media.audio.speech_to_text(
            FLOW_SHEET,
            audio_stream=read_audio(),
        )).is_err():
            print("error", ret.err_value)
            return {"error": ret.err_value}

        async for msg in ret.ok_value:
            print(msg)
            await websocket.send_json(msg)

    except WebSocketDisconnect:
        print("WebSocket disconnected")


@app.get("/")
async def root():
    return {
        "message": "Flowster Server",
        "endpoint": "/stream",
        "info": "Connect to /stream to receive server-sent events"
    }


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    print(f"Using port {port}")
    import uvicorn
    uvicorn.run('main:app', host="0.0.0.0", port=port, reload=True)#, log_level="debug")

