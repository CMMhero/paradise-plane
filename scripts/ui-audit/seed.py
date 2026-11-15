# Bootstrap a fresh local Paradise instance so `manage.py seed_demo_data` can run.
#
#   sudo docker compose -f docker-compose-local.yml exec -T \
#       -e UI_AUDIT_EMAIL=... -e UI_AUDIT_PASSWORD=... api \
#       python manage.py shell --settings=plane.settings.local < scripts/ui-audit/seed.py
#
# Idempotent. Creates: the instance (setup done), a Super Admin user with a
# completed profile, and the workspace `pt-paradise-perkasa` owned by that user.
# The org content itself (divisions, departments, ~56 accounts, ~170 work items,
# modules, pages, labels, approvals ...) comes from the repo's own seed command:
#
#   sudo docker compose -f docker-compose-local.yml exec api \
#       python manage.py seed_demo_data --settings=plane.settings.local
#
# Credentials come from the environment only; nothing is written to disk.
import os

from plane.db.models import Profile, User, Workspace, WorkspaceMember
from plane.db.superadmin import angkat_super_admin
from plane.license.models import Instance

EMAIL = os.environ["UI_AUDIT_EMAIL"]
PASSWORD = os.environ["UI_AUDIT_PASSWORD"]
WS_SLUG = os.environ.get("UI_AUDIT_WORKSPACE", "pt-paradise-perkasa")
WS_NAME = "PT Paradise Perkasa"

instance = Instance.objects.last()
if instance is None:
    raise SystemExit("no Instance row yet: start the api container first (register_instance)")
if not instance.is_setup_done:
    instance.is_setup_done = True
    instance.is_verified = True
    instance.instance_name = instance.instance_name or "Paradise Task Tracker"
    instance.save()

user, created = User.objects.get_or_create(
    email=EMAIL,
    defaults={"username": EMAIL, "display_name": "Admin UI Audit", "first_name": "Admin", "last_name": "Audit"},
)
user.is_active = True
user.is_email_verified = True
user.is_password_autoset = False
user.is_password_reset_required = False
user.set_password(PASSWORD)
user.save()

profile, _ = Profile.objects.get_or_create(user=user)
profile.is_onboarded = True
profile.is_tour_completed = True
profile.onboarding_step = {
    "profile_complete": True,
    "workspace_create": True,
    "workspace_invite": True,
    "workspace_join": True,
}
profile.save()

ws = Workspace.objects.filter(slug=WS_SLUG).first()
if ws is None:
    ws = Workspace.objects.create(name=WS_NAME, slug=WS_SLUG, owner=user, timezone="Asia/Jakarta")
WorkspaceMember.objects.update_or_create(
    workspace=ws, member=user, defaults={"role": 20, "is_active": True}
)
angkat_super_admin(instance, user)
print(f"ok: user created={created} workspace={ws.slug} instance_setup_done={instance.is_setup_done}")
