import React, {useState, useRef, useEffect, forwardRef} from 'react'
import {
    Send,
    Paperclip,
    Mic,
    EditIcon,
    PlusIcon,
    BrainIcon,
    PlusCircleIcon, DownloadIcon
} from 'lucide-react'
import * as Util from "../helpers/util.js"
import { TypingIndicator } from "../components/typing_indicator.jsx";
import { marked } from 'marked';
//import 'github-markdown-css/github-markdown.css';
import 'github-markdown-css/github-markdown-light.css';
import { XMarkIcon } from "@heroicons/react/20/solid";
import {
    BarsArrowDownIcon,
    CheckCircleIcon
} from "@heroicons/react/24/outline/index";
import { NameField } from "../components/name_field.jsx";
import { Microphone } from "../components/microphone.jsx";
import {WEB_URL, WS_URL} from "../settings";
import { ChatTextArea } from "../components/chat_text_area.jsx";
import {
    MarkdownViewer,
    saveAsMarkdown
} from "../components/markdown_viewer.jsx";
import {Conversation} from "../components/conversation.jsx";
const wsUrl = `${WS_URL}/api/speech_to_text`;



export const ChatInterface = props => {
    const {showToast} = props
    const [contexts, setContexts] = useState([])
    const [scrollLock, setScrollLock] = useState(false)

    const [state, setState] = useState({
        importFileModalOpen: false,
    })
    const { importFileModalOpen } = state

    const messagesEndRef = useRef(null)
    const chatTextAreaRef = useRef(null)
    const conversationRef = useRef(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    const handleMessageChange = () => {
        if ( scrollLock ) {
            scrollToBottom()
        }
    }

    //Get the query param initial, if it exists and is not empty, then fill the send a query right now
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const initial = params.get('initial')
        if ( initial && initial.trim() !== '' ) {
            handleSend(initial)
        }
    }, [])

    const prevScrollYRef = useRef(0);
    useEffect(() => {
        //if (!scrollLock) {
            //return
        //}

        const onScroll = () => {
            const currentScrollY = window.scrollY ?? window.pageYOffset;
            const prevScrollY   = prevScrollYRef.current;

            if (currentScrollY > prevScrollY) {
                //
            } else if (currentScrollY < prevScrollY) {
                setScrollLock(false)
            }

            prevScrollYRef.current = currentScrollY;
        };

        window.addEventListener('scroll', onScroll, { passive: true });

        return () => window.removeEventListener('scroll', onScroll);
    }, [])

    const handleRetry = (content) => {
        chatTextAreaRef.current.setMessage(content)
    }

    const handleSend = (message, model) => {
        conversationRef.current.handleSend(message, model, contexts)
        setScrollLock(true)
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-gray-50">
            <Conversation
                ref={conversationRef}
                onMessageChange={handleMessageChange}
                onRetry={handleRetry}
                onStreamEnd={() => setScrollLock(false)}
                showToast={showToast}
            />
            
            <div ref={messagesEndRef} />

            {/* Single input field for name, label of context size, trash can at end, stack theses up with flex  */}
            {contexts.length > 0 &&
            <div className="flex flex-row flex-wrap w-full sm:pl-12 sm:pr-6 bg-white">
                {contexts.map((ctx, idx) => (
                    <NameField
                        key={idx}
                        solo={contexts.length === 1}
                        name={ctx.name}
                        content={ctx.content}
                        file_type={ctx.file_type}
                        onNameChange={(name) => {
                            setContexts(prev => {
                                const updated = [...prev]
                                updated[idx].name = name
                                return updated
                            })
                        }}
                        onContentChange={(content) => {
                            setContexts(prev => {
                                const updated = [...prev]
                                updated[idx].content = content
                                return updated
                            })
                        }}
                        onContentAppend={(content) => {
                            setContexts(prev => {
                                const updated = [...prev]
                                console.log(updated[idx].content, content)
                                updated[idx].content += content
                                return updated
                            })
                        }}
                        onDelete={() => {
                            setContexts(prev => {
                                const updated = [...prev]
                                updated.splice(idx, 1)
                                return updated
                            })
                        }}
                        showToast={showToast}
                        />
                ))}
            </div>
            }

            <div className="h-32 bg-gray-50"></div>

            <ChatTextArea
                ref={chatTextAreaRef}
                className="border-t"
                content_count={contexts.length}
                onSend={handleSend}
                showToast={showToast}
            />
        </div>
    )
}
