from asgiref.sync import sync_to_async
from django.db import models
from django.contrib import admin
import uuid


class ChatSession(models.Model):
    id = models.AutoField(primary_key=True)

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    suggested_consultation = models.BooleanField(default=False)
    profile = models.JSONField(blank=True, null=True)

    timestamp_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'website'

    def __str__(self):
        return self.name

    @staticmethod
    async def getByUid(uid):
        try:
            return await sync_to_async( ChatSession.objects.get )(uid=uid)
        except ChatSession.DoesNotExist:
            return None

    @staticmethod
    async def getOrCreateByUid(uid, name):
        if (chat_session := await ChatSession.getByUid(uid)) is None:
            chat_session = await sync_to_async( ChatSession.objects.create )(name=name[:255])

        return chat_session

    def toJson(self):
        return {
            'uid': str(self.uid),
            'name': str(self.name),
            'suggested_consultation': self.suggested_consultation,
            'profile': self.profile,
            'timestamp_on': self.timestamp_on.isoformat(),
        }

    @staticmethod
    def customAdmin ():
        from website.models.prompt import Prompt

        class PromptInline(admin.TabularInline):
            model = Prompt
            fields = ('type', 'content', 'thinking', 'extra')
            extra = 0


        class Admin(admin.ModelAdmin):
            list_display = ('name', 'suggested_consultation', 'timestamp_on')
            fields = ('uid', 'name', 'suggested_consultation', 'profile', 'timestamp_on')
            readonly_fields = ('timestamp_on', 'uid')
            inlines = [PromptInline]

        return Admin
