# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Custom Properties
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from uuid import uuid4

# Django imports
from django.utils.text import slugify

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet, BaseAPIView
from plane.app.serializers import (
    IssuePropertySerializer,
    IssuePropertyOptionSerializer,
    IssuePropertyValueSerializer,
)
from plane.app.permissions import allow_permission, ProjectBasePermission, ProjectEntityPermission, ROLE
from plane.db.models import IssueProperty, IssuePropertyOption, IssuePropertyValue


class IssuePropertyViewSet(BaseViewSet):
    serializer_class = IssuePropertySerializer
    model = IssueProperty
    permission_classes = [ProjectBasePermission]

    def get_queryset(self):
        return (
            IssueProperty.objects.filter(
                workspace__slug=self.kwargs.get("slug"),
                project_id=self.kwargs.get("project_id"),
                issue_type_id=self.kwargs.get("type_id"),
            )
            .prefetch_related("options")
            .order_by("sort_order")
        )

    def list(self, request, slug, project_id, type_id):
        serializer = IssuePropertySerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id, type_id):
        serializer = IssuePropertySerializer(data=request.data)
        if serializer.is_valid():
            # Kunci internal `name` diturunkan dari display_name (+ suffix unik anti-tabrakan)
            base = slugify(serializer.validated_data.get("display_name", "")).replace("-", "_") or "field"
            name = f"{base}_{uuid4().hex[:6]}"
            serializer.save(project_id=project_id, issue_type_id=type_id, name=name)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, type_id, pk):
        prop = self.get_queryset().get(pk=pk)
        serializer = IssuePropertySerializer(prop, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, type_id, pk):
        self.get_queryset().get(pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IssuePropertyOptionViewSet(BaseViewSet):
    serializer_class = IssuePropertyOptionSerializer
    model = IssuePropertyOption
    permission_classes = [ProjectBasePermission]

    def get_queryset(self):
        return IssuePropertyOption.objects.filter(
            workspace__slug=self.kwargs.get("slug"),
            project_id=self.kwargs.get("project_id"),
            property_id=self.kwargs.get("property_id"),
        ).order_by("sort_order")

    def list(self, request, slug, project_id, property_id):
        serializer = IssuePropertyOptionSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id, property_id):
        serializer = IssuePropertyOptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project_id=project_id, property_id=property_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, property_id, pk):
        option = self.get_queryset().get(pk=pk)
        serializer = IssuePropertyOptionSerializer(option, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, property_id, pk):
        self.get_queryset().get(pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IssuePropertyValueEndpoint(BaseAPIView):
    """Baca & set nilai property custom untuk satu work item (anggota project)."""

    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id, issue_id):
        values = IssuePropertyValue.objects.filter(
            workspace__slug=slug, project_id=project_id, issue_id=issue_id
        )
        serializer = IssuePropertyValueSerializer(values, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, slug, project_id, issue_id):
        property_id = request.data.get("property")
        if not property_id:
            return Response({"error": "property wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        # Pastikan property memang milik project ini
        prop = IssueProperty.objects.filter(
            workspace__slug=slug, project_id=project_id, pk=property_id
        ).first()
        if not prop:
            return Response({"error": "Property tidak ditemukan di project ini."}, status=status.HTTP_404_NOT_FOUND)

        # Validasi nilai sesuai tipe field
        error = self._validate_typed_value(prop, request.data)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Replace: hapus nilai lama property ini untuk issue, buat baru
        IssuePropertyValue.objects.filter(
            project_id=project_id, issue_id=issue_id, property_id=property_id
        ).delete()

        serializer = IssuePropertyValueSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project_id=project_id, issue_id=issue_id, property_id=property_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _validate_typed_value(prop, data):
        """Pastikan kolom nilai yang terisi cocok dengan property_type field."""
        ptype = prop.property_type
        if ptype == "TEXT" and not (data.get("value_text") or "").strip():
            return "Field teks butuh value_text."
        if ptype == "DECIMAL" and data.get("value_number") is None:
            return "Field angka butuh value_number."
        if ptype == "DATETIME" and not data.get("value_datetime"):
            return "Field tanggal butuh value_datetime."
        if ptype in ("OPTION", "MEMBER") and not data.get("value_uuid"):
            return f"Field {ptype.lower()} butuh value_uuid."
        if ptype == "OPTION":
            from plane.db.models import IssuePropertyOption

            if not IssuePropertyOption.objects.filter(property=prop, pk=data.get("value_uuid")).exists():
                return "value_uuid bukan opsi yang valid untuk field ini."
        if ptype == "MEMBER":
            from plane.db.models import ProjectMember

            if not ProjectMember.objects.filter(
                project_id=prop.project_id, member_id=data.get("value_uuid"), is_active=True
            ).exists():
                return "value_uuid bukan anggota project ini."
        return None
