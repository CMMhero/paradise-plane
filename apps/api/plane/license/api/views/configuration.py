# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from smtplib import (
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
    SMTPServerDisconnected,
)

# Django imports
from django.core.mail import BadHeaderError, EmailMultiAlternatives, get_connection
from django.db.models import Q, Case, When, Value

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.license.api.permissions import InstanceAdminPermission
from plane.license.models import InstanceConfiguration
from plane.license.api.serializers import InstanceConfigurationSerializer
from plane.license.utils.encryption import encrypt_data
from plane.utils.cache import cache_response, invalidate_cache
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.instance_config_variables import instance_config_variables
from plane.utils.saklar_instance import SAKLAR_BAWAAN, SETELAN_ANGKA, nilai_angka_sah
from plane.utils.bawaan_member import KUNCI as BAWAAN_MEMBER_KUNCI
from plane.utils.bawaan_project import KUNCI as BAWAAN_PROJECT_KUNCI

_KUNCI_DIKENAL = {item["key"]: item for item in instance_config_variables}


class InstanceConfigurationEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    @cache_response(60 * 60 * 2, user=False)
    def get(self, request):
        instance_configurations = InstanceConfiguration.objects.all()
        serializer = InstanceConfigurationSerializer(instance_configurations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @invalidate_cache(path="/api/instances/configurations/", user=False)
    @invalidate_cache(path="/api/instances/", user=False)
    def patch(self, request):
        # Bawaan member baru punya endpoint sendiri yang memeriksa isinya; lewat
        # sini JSON sembarang akan tersimpan tanpa dicek (KEP-44).
        if BAWAAN_MEMBER_KUNCI in request.data:
            return Response(
                {"error": f"{BAWAAN_MEMBER_KUNCI} is changed via /api/instances/members/defaults/."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if BAWAAN_PROJECT_KUNCI in request.data:
            return Response(
                {"error": f"{BAWAAN_PROJECT_KUNCI} is changed via /api/instances/projects/defaults/."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Saklar fitur Paradise hanya "0"/"1": nilai lain dibaca sebagai mati oleh
        # `saklar_aktif`, jadi typo diam-diam mematikan fitur.
        salah = [
            k for k in request.data.keys() if k in SAKLAR_BAWAAN and str(request.data[k]).strip() not in ("0", "1")
        ]
        if salah:
            return Response(
                {"error": f"Toggle values must be 0 or 1: {', '.join(salah)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Setelan angka dijaga rentangnya di sini, bukan hanya di form: retensi
        # 0 hari berarti task harian menghapus seluruh riwayat.
        di_luar = [k for k in request.data.keys() if k in SETELAN_ANGKA and not nilai_angka_sah(k, request.data[k])]
        if di_luar:
            rentang = ", ".join(f"{k} ({SETELAN_ANGKA[k][1]}-{SETELAN_ANGKA[k][2]})" for k in di_luar)
            return Response(
                {"error": f"Value out of range: {rentang}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Kunci yang dikenal tapi barisnya belum ada (instance lama yang belum
        # menjalankan `configure_instance` sesudah kunci itu ditambahkan) dibuat
        # dulu. Tanpa ini PATCH membalas 200 tanpa menulis apa pun.
        yang_ada = set(InstanceConfiguration.objects.filter(key__in=request.data.keys()).values_list("key", flat=True))
        for kunci in request.data.keys():
            item = _KUNCI_DIKENAL.get(kunci)
            if item and kunci not in yang_ada:
                InstanceConfiguration.objects.get_or_create(
                    key=kunci,
                    defaults={"category": item["category"], "is_encrypted": item.get("is_encrypted", False)},
                )

        configurations = InstanceConfiguration.objects.filter(key__in=request.data.keys())

        bulk_configurations = []
        for configuration in configurations:
            raw_value = request.data.get(configuration.key, configuration.value)
            value = "" if raw_value is None else str(raw_value).strip()
            if configuration.is_encrypted:
                configuration.value = encrypt_data(value)
            else:
                configuration.value = value
            bulk_configurations.append(configuration)

        InstanceConfiguration.objects.bulk_update(bulk_configurations, ["value"], batch_size=100)

        serializer = InstanceConfigurationSerializer(configurations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DisableEmailFeatureEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    @invalidate_cache(path="/api/instances/", user=False)
    def delete(self, request):
        try:
            InstanceConfiguration.objects.filter(
                Q(
                    key__in=[
                        "EMAIL_HOST",
                        "EMAIL_HOST_USER",
                        "EMAIL_HOST_PASSWORD",
                        "ENABLE_SMTP",
                        "EMAIL_PORT",
                        "EMAIL_FROM",
                    ]
                )
            ).update(value=Case(When(key="ENABLE_SMTP", then=Value("0")), default=Value("")))
            return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Failed to disable email configuration"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmailCredentialCheckEndpoint(BaseAPIView):
    def post(self, request):
        receiver_email = request.data.get("receiver_email", False)
        if not receiver_email:
            return Response(
                {"error": "Receiver email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        (
            EMAIL_HOST,
            EMAIL_HOST_USER,
            EMAIL_HOST_PASSWORD,
            EMAIL_PORT,
            EMAIL_USE_TLS,
            EMAIL_USE_SSL,
            EMAIL_FROM,
        ) = get_email_configuration()

        # Configure all the connections
        connection = get_connection(
            host=EMAIL_HOST,
            port=int(EMAIL_PORT),
            username=EMAIL_HOST_USER,
            password=EMAIL_HOST_PASSWORD,
            use_tls=EMAIL_USE_TLS == "1",
            use_ssl=EMAIL_USE_SSL == "1",
        )
        # Prepare email details
        subject = "Notifikasi email dari Paradise Task Tracker"
        message = "Ini contoh notifikasi email yang dikirim dari Paradise Task Tracker."
        # Send the email
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=EMAIL_FROM,
                to=[receiver_email],
                connection=connection,
            )
            msg.send(fail_silently=False)
            return Response({"message": "Email successfully sent."}, status=status.HTTP_200_OK)
        except BadHeaderError:
            return Response({"error": "Invalid email header."}, status=status.HTTP_400_BAD_REQUEST)
        except SMTPAuthenticationError:
            return Response(
                {"error": "Invalid credentials provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPConnectError:
            return Response(
                {"error": "Could not connect with the SMTP server."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPSenderRefused:
            return Response(
                {"error": "From address is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPServerDisconnected:
            return Response(
                {"error": "SMTP server disconnected unexpectedly."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPRecipientsRefused:
            return Response(
                {"error": "All recipient addresses were refused."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TimeoutError:
            return Response(
                {"error": "Timeout error while trying to connect to the SMTP server."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ConnectionError:
            return Response(
                {"error": "Network connection error. Please check your internet connection."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"error": "Could not send email. Please check your configuration"},
                status=status.HTTP_400_BAD_REQUEST,
            )
