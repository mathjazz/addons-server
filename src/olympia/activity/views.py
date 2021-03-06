from django.shortcuts import get_object_or_404

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from olympia import amo
from olympia.activity.serializers import ActivityLogSerializer
from olympia.addons.views import AddonChildMixin
from olympia.api.permissions import (
    AllowAddonAuthor, AllowReviewer, AllowReviewerUnlisted, AnyOf)
from olympia.devhub.models import ActivityLog
from olympia.versions.models import Version


class VersionReviewNotesViewSet(AddonChildMixin, RetrieveModelMixin,
                                ListModelMixin, GenericViewSet):
    permission_classes = [
        AnyOf(AllowAddonAuthor, AllowReviewer, AllowReviewerUnlisted),
    ]
    serializer_class = ActivityLogSerializer
    queryset = ActivityLog.objects.all()

    def get_queryset(self):
        addon = self.get_addon_object()
        version_object = get_object_or_404(
            Version.unfiltered.filter(addon=addon),
            pk=self.kwargs['version_pk'])
        alog = ActivityLog.objects.for_version(version_object)
        return alog.filter(action__in=amo.LOG_REVIEW_QUEUE_DEVELOPER)

    def get_addon_object(self):
        return super(VersionReviewNotesViewSet, self).get_addon_object(
            permission_classes=self.permission_classes)

    def check_object_permissions(self, request, obj):
        """Check object permissions against the Addon, not the ActivityLog."""
        # Just loading the add-on object triggers permission checks, because
        # the implementation in AddonChildMixin calls AddonViewSet.get_object()
        self.get_addon_object()

    def get_serializer_context(self):
        ctx = super(VersionReviewNotesViewSet, self).get_serializer_context()
        ctx['to_highlight'] = self.pending_queryset(
            amo.LOG.DEVELOPER_REPLY_VERSION)
        return ctx

    def pending_queryset(self, log_type):
        version_qs = self.get_queryset()
        latest_reply = version_qs.filter(action=log_type.id).first()
        if not latest_reply:
            return version_qs
        return version_qs.filter(created__gt=latest_reply.created)
