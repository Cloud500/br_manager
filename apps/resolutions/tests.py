"""Tests for resolutions app."""

from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.agendas.forms import AgendaItemResolutionForm
from apps.agendas.models import AgendaItem
from apps.committees.factories import (
    MainCommitteeFactory,
    RegularMembershipFactory,
    SubcommitteeFactory,
)
from apps.meetings.models import Meeting
from apps.participants.models import MeetingParticipant
from apps.protocols.models import ProtocolEntry
from apps.resolutions.models import Resolution
from apps.resolutions.services import ResolutionDecisionService
from apps.roles.models import Permission, Role, RolePermission


class ResolutionModelTest(TestCase):
    """Tests for Resolution model behavior."""

    def test_can_save_multiple_draft_resolutions_with_empty_number(self):
        """Draft resolutions can share an empty resolution number."""
        committee = MainCommitteeFactory.create(can_create_resolutions=True)
        user = UserFactory.create()

        first = Resolution(
            committee=committee,
            title="First draft resolution",
            description="First draft resolution",
            created_by=user,
            status="DRAFT",
        )
        first.save()

        second = Resolution(
            committee=committee,
            title="Second draft resolution",
            description="Second draft resolution",
            created_by=user,
            status="DRAFT",
        )
        second.save()

        self.assertEqual(Resolution.objects.filter(committee=committee).count(), 2)

    def test_resolution_str_uses_title(self):
        """Resolution string representation includes the title."""
        committee = MainCommitteeFactory.create(can_create_resolutions=True)
        user = UserFactory.create()

        resolution = Resolution.objects.create(
            committee=committee,
            title="Neuer Beschluss",
            description="Beschlussbeschreibung",
            created_by=user,
            status="DRAFT",
        )

        self.assertEqual(str(resolution), "Entwurf - Neuer Beschluss")

    def test_record_result_updates_resolution_and_protocol_entry(self):
        """Decision results are stored on the resolution and mirrored to protocol."""
        committee = MainCommitteeFactory.create(can_create_resolutions=True)
        actor = UserFactory.create()
        membership = RegularMembershipFactory.create(user=actor, committee=committee)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Beschluss-Sitzung",
            date=date.today(),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/resolution",
            created_by=actor,
            status="IN_PROGRESS",
        )
        MeetingParticipant.objects.filter(
            meeting=meeting, membership=membership
        ).update(
            attendance_status=MeetingParticipant.ATTENDANCE_PRESENT,
            last_self_confirmed_at=meeting.created_at,
            last_written_confirmed_at=meeting.created_at,
        )
        resolution = Resolution.objects.create(
            committee=committee,
            title="Beschluss",
            description="Beschreibung",
            created_by=actor,
            status="PROPOSED",
        )
        item = AgendaItem.objects.create(
            agenda=meeting.agenda,
            title="Beschluss",
            sort_order=1,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        resolution_item = resolution.agenda_items.create(agenda_item=item)
        resolution.title = "Nachträglich geänderter Beschluss"
        resolution.description = "Nachträglich geänderte Beschreibung"
        resolution.save(update_fields=["title", "description", "updated_at"])

        with self.assertRaises(ValidationError):
            ResolutionDecisionService.record_result(
                resolution_agenda_item=resolution_item,
                yes_votes=2,
                no_votes=0,
                abstentions=0,
                is_quorate=True,
                actor=actor,
            )

        meeting.current_agenda_item = item
        meeting.save(update_fields=["current_agenda_item", "updated_at"])
        result = ResolutionDecisionService.record_result(
            resolution_agenda_item=resolution_item,
            yes_votes=1,
            no_votes=0,
            abstentions=0,
            is_quorate=True,
            quorum_manually_overridden=True,
            quorum_override_reason="",
            decision_text='<p onclick="bad()">OK</p><script>alert(1)</script><a href="javascript:bad()">x</a><strong>Beschlussfassung</strong>',
            actor=actor,
        )

        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(result.yes_votes, 1)
        self.assertTrue(result.quorum_manually_overridden)
        self.assertEqual(result.quorum_override_reason, "")
        self.assertIn("Beschlussfassung", result.decision_text)
        self.assertIn("<strong>Beschlussfassung</strong>", result.decision_text)
        self.assertNotIn("onclick", result.decision_text)
        self.assertNotIn("script", result.decision_text)
        self.assertNotIn("javascript:", result.decision_text)
        entry = ProtocolEntry.objects.get(object_ref=f"resolution:{resolution.pk}")
        self.assertEqual(entry.entry_type, ProtocolEntry.ENTRY_RESOLUTION)
        self.assertEqual(entry.title, "Beschluss")
        self.assertEqual(entry.data["agenda_item_title"], "Beschluss")
        self.assertEqual(entry.data["agenda_item_description"], "Beschreibung")
        self.assertEqual(entry.data["yes_votes"], 1)
        self.assertIn("Beschlussfassung", entry.data["decision_text"])


class ResolutionDetailViewTest(TestCase):
    """Tests for resolution detail view."""

    def setUp(self):
        from apps.roles.models import Permission, Role

        self.user = UserFactory.create()
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        # Create role with view permission
        view_permission = Permission.objects.get(codename="resolution.view")
        role = Role.objects.create(name="Viewer", role_type="COMMITTEE")
        role.permissions.add(view_permission)
        self.membership = RegularMembershipFactory.create(
            user=self.user, committee=self.committee, role=role
        )
        self.client.force_login(self.user)

    def test_approved_resolution_shows_decision_text(self):
        """Detail view shows decision_text for approved/rejected resolutions."""
        resolution = Resolution.objects.create(
            committee=self.committee,
            title="Genehmigter Beschluss",
            description="Beschreibung des Vorschlags",
            decision_text="<p><strong>Beschlossen:</strong> Budget wird freigegeben.</p>",
            status="APPROVED",
            yes_votes=5,
            no_votes=1,
            abstentions=0,
            is_quorate=True,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("resolutions:resolution_detail", args=[resolution.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beschlussfassung")
        self.assertContains(response, "Beschlossen:")
        self.assertContains(response, "Budget wird freigegeben")
        self.assertContains(response, "Beschreibung des Vorschlags")

    def test_draft_resolution_does_not_show_decision_text(self):
        """Draft resolutions don't show the decision text section."""
        resolution = Resolution.objects.create(
            committee=self.committee,
            title="Entwurf",
            description="Nur Entwurf",
            status="DRAFT",
            created_by=self.user,
        )

        response = self.client.get(
            reverse("resolutions:resolution_detail", args=[resolution.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Beschlussfassung")
        self.assertContains(response, "Nur Entwurf")


class ResolutionCreateViewTest(TestCase):
    """Tests for resolution creation view."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.url = reverse("resolutions:resolution_create")

    def test_superuser_can_create_multiple_draft_resolutions(self):
        """A superuser can create multiple draft resolutions for one committee."""
        payload = {
            "committee": str(self.committee.pk),
            "title": "Neuer Beschluss",
            "description": "Draft resolution description",
            "propose_to_main_committee": "",
        }

        first_response = self.client.post(self.url, payload)
        second_response = self.client.post(self.url, payload)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(
            Resolution.objects.filter(committee=self.committee).count(),
            2,
        )

    def test_create_view_accepts_title(self):
        """The create view persists the submitted title."""
        payload = {
            "committee": str(self.committee.pk),
            "title": "Titel aus dem Formular",
            "description": "Beschreibung aus dem Formular",
            "propose_to_main_committee": "",
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, 302)
        resolution = Resolution.objects.latest("created_at")
        self.assertEqual(resolution.title, "Titel aus dem Formular")
        self.assertEqual(resolution.description, "Beschreibung aus dem Formular")

    def test_main_committee_without_resolution_flag_returns_form_error(self):
        """Invalid main committee selection renders a form error instead of a 500."""
        committee = MainCommitteeFactory.create(can_create_resolutions=False)
        payload = {
            "committee": str(committee.pk),
            "title": "Draft resolution",
            "description": "Draft resolution description",
            "propose_to_main_committee": "",
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "committee",
            "Dieses Gremium darf keine Beschlüsse erstellen",
        )
        self.assertFalse(Resolution.objects.filter(committee=committee).exists())


class ResolutionCreateFromAgendaViewTest(TestCase):
    """Tests for creating a resolution directly from a meeting agenda."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Sitzung",
            date=date.today(),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/meeting",
            created_by=self.user,
        )
        self.agenda = self.meeting.agenda

    def _create_role(self, codename, permission_codenames):
        """Create a committee role with the requested permissions."""
        role = Role.objects.create(
            name=codename,
            codename=codename,
            role_type="COMMITTEE",
            is_system_role=False,
        )
        for permission_codename in permission_codenames:
            permission, _created = Permission.objects.get_or_create(
                codename=permission_codename,
                defaults={
                    "name": permission_codename,
                    "category": permission_codename.split(".")[0],
                },
            )
            RolePermission.objects.create(role=role, permission=permission)
        return role

    def test_add_resolution_page_links_to_preselected_resolution_create(self):
        """The add-resolution page offers direct resolution creation for the meeting."""
        response = self.client.get(
            reverse(
                "agendas:item_resolution_create", kwargs={"agenda_id": self.agenda.pk}
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Neuen Beschluss erstellen")
        self.assertContains(
            response,
            f"{reverse('resolutions:resolution_create')}?agenda={self.agenda.pk}",
        )

    def test_direct_resolution_create_from_agenda_requires_login(self):
        """Anonymous access follows the normal login redirect instead of RBAC checks."""
        self.client.logout()

        response = self.client.get(
            f"{reverse('resolutions:resolution_create')}?agenda={self.agenda.pk}"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_add_resolution_page_requires_login_before_locked_status(self):
        """Anonymous agenda access does not leak locked meeting state."""
        self.meeting.status = "COMPLETED"
        self.meeting.save(update_fields=["status", "updated_at"])
        self.client.logout()

        response = self.client.get(
            reverse(
                "agendas:item_resolution_create", kwargs={"agenda_id": self.agenda.pk}
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_add_resolution_page_hides_direct_create_for_invalid_committee(self):
        """The shortcut is hidden when the meeting committee cannot create resolutions."""
        committee = MainCommitteeFactory.create(can_create_resolutions=False)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Sitzung ohne Beschlüsse",
            date=date.today(),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/no-resolution",
            created_by=self.user,
        )

        response = self.client.get(
            reverse(
                "agendas:item_resolution_create",
                kwargs={"agenda_id": meeting.agenda.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Neuen Beschluss erstellen")

    def test_resolution_create_from_agenda_prefills_meeting_committee(self):
        """The source meeting committee is preselected and is the only choice."""
        response = self.client.get(
            f"{reverse('resolutions:resolution_create')}?agenda={self.agenda.pk}"
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial["committee"], self.committee)
        self.assertQuerySetEqual(
            form.fields["committee"].queryset,
            [self.committee],
            transform=lambda committee: committee,
        )

    def test_resolution_create_from_agenda_creates_proposed_resolution_top(self):
        """Submitting from a meeting creates and links the resolution as agenda TOP."""
        response = self.client.post(
            f"{reverse('resolutions:resolution_create')}?agenda={self.agenda.pk}",
            {
                "committee": str(self.committee.pk),
                "title": "Direkter Beschluss",
                "description": "Beschreibung für den TOP",
                "propose_to_main_committee": "",
            },
        )

        resolution = Resolution.objects.get(title="Direkter Beschluss")
        agenda_item = AgendaItem.objects.get(
            agenda=self.agenda, title="Direkter Beschluss"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk}),
        )
        self.assertEqual(resolution.committee, self.committee)
        self.assertEqual(resolution.status, "PROPOSED")
        self.assertEqual(resolution.description, "Beschreibung für den TOP")
        self.assertEqual(agenda_item.description, "Beschreibung für den TOP")
        self.assertEqual(agenda_item.item_type, AgendaItem.TYPE_RESOLUTION)
        self.assertEqual(agenda_item.resolution_link.resolution, resolution)

    def test_direct_create_requires_resolution_propose_permission(self):
        """Direct TOP creation must not bypass the resolution proposal permission."""
        role = self._create_role(
            "DIRECT_RESOLUTION_CREATOR_WITHOUT_PROPOSE",
            ["agenda.add_item_resolution", "resolution.create"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            f"{reverse('resolutions:resolution_create')}?agenda={self.agenda.pk}",
            {
                "committee": str(self.committee.pk),
                "title": "Unerlaubter Beschluss",
                "description": "Beschlussbeschreibung",
                "propose_to_main_committee": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk}),
        )
        self.assertFalse(
            Resolution.objects.filter(title="Unerlaubter Beschluss").exists()
        )
        self.assertFalse(AgendaItem.objects.filter(agenda=self.agenda).exists())

    def test_ba_member_can_directly_create_for_main_meeting(self):
        """The MAIN/BA agenda permission special case works for the shortcut."""
        ba = SubcommitteeFactory.create(
            parent=self.committee,
            committee_type="COMMITTEE",
            can_create_resolutions=True,
        )
        role = self._create_role(
            "BA_DIRECT_RESOLUTION_CREATOR",
            ["agenda.add_item_resolution", "resolution.create", "resolution.propose"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=ba, role=role)
        self.client.force_login(user)

        response = self.client.post(
            f"{reverse('resolutions:resolution_create')}?agenda={self.agenda.pk}",
            {
                "committee": str(self.committee.pk),
                "title": "BA-Beschlussvorschlag",
                "description": "BA-Beschreibung",
                "propose_to_main_committee": "",
            },
        )

        resolution = Resolution.objects.get(title="BA-Beschlussvorschlag")
        agenda_item = AgendaItem.objects.get(
            agenda=self.agenda, title="BA-Beschlussvorschlag"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk}),
        )
        self.assertEqual(resolution.committee, self.committee)
        self.assertEqual(resolution.status, "PROPOSED")
        self.assertEqual(agenda_item.description, "BA-Beschreibung")
        self.assertEqual(agenda_item.resolution_link.resolution, resolution)


class AgendaItemResolutionFormTest(TestCase):
    """Tests for resolution TOP form behavior."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Sitzung",
            date=date.today(),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/meeting",
            created_by=self.user,
        )
        self.agenda = self.meeting.agenda

    def test_blank_title_uses_resolution_title(self):
        """An empty TOP title falls back to the resolution title."""
        resolution = Resolution.objects.create(
            committee=self.committee,
            title="Beschluss-Titel",
            description="Beschreibung des Beschlusses",
            created_by=self.user,
            status="PROPOSED",
        )

        form = AgendaItemResolutionForm(
            data={
                "resolution": str(resolution.pk),
                "title": "",
                "description": "",
                "parent": "",
            },
            agenda=self.agenda,
        )

        self.assertTrue(form.is_valid(), form.errors)
        item = form.save()
        self.assertEqual(item.title, "Beschluss-Titel")
        self.assertEqual(item.description, "Beschreibung des Beschlusses")


class AgendaItemResolutionViewTest(TestCase):
    """Tests for resolution agenda item update/delete flows."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Sitzung",
            date=date.today(),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/meeting",
            created_by=self.user,
        )
        self.agenda = self.meeting.agenda
        self.resolution = Resolution.objects.create(
            committee=self.committee,
            title="Beschluss-Titel",
            description="Beschlussbeschreibung",
            created_by=self.user,
            status="PROPOSED",
        )
        self.item = AgendaItem.objects.create(
            agenda=self.agenda,
            title="Beschluss-Titel",
            description="Alt",
            sort_order=1,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        self.resolution.agenda_items.create(agenda_item=self.item)

    def _create_role(self, codename, permission_codenames):
        """Create a committee role with the requested permissions."""
        role = Role.objects.create(
            name=codename,
            codename=codename,
            role_type="COMMITTEE",
            is_system_role=False,
        )
        for permission_codename in permission_codenames:
            permission, _created = Permission.objects.get_or_create(
                codename=permission_codename,
                defaults={
                    "name": permission_codename,
                    "category": permission_codename.split(".")[0],
                },
            )
            RolePermission.objects.create(role=role, permission=permission)
        return role

    def test_resolution_item_update_keeps_resolution_snapshot_text(self):
        """Resolution TOP title and description stay as the linked resolution snapshot."""
        update_url = reverse("agendas:item_update", kwargs={"pk": self.item.pk})

        update_response = self.client.post(
            update_url,
            {
                "title": "Neuer TOP-Titel",
                "description": "Neue Beschreibung",
                "parent": "",
            },
        )

        self.assertEqual(update_response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Beschluss-Titel")
        self.assertEqual(self.item.description, "Beschlussbeschreibung")

    def test_resolution_item_model_rejects_snapshot_text_changes(self):
        """Direct model saves cannot bypass resolution TOP snapshot text protection."""
        self.item.title = "Direkte Änderung"
        self.item.description = "Direkt geänderte Beschreibung"

        with self.assertRaises(ValidationError):
            self.item.save()

        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Beschluss-Titel")
        self.assertEqual(self.item.description, "Beschlussbeschreibung")

    def test_resolution_item_model_rejects_type_or_agenda_changes(self):
        """Direct model saves cannot break resolution TOP identity."""
        self.item.item_type = AgendaItem.TYPE_REGULAR

        with self.assertRaises(ValidationError):
            self.item.save()

        other_meeting = Meeting.objects.create(
            committee=self.committee,
            title="Andere Sitzung",
            date=date.today(),
            start_time=time(11, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/other-meeting",
            created_by=self.user,
        )
        self.item.refresh_from_db()
        self.item.agenda = other_meeting.agenda

        with self.assertRaises(ValidationError):
            self.item.save()

        self.item.refresh_from_db()
        self.assertEqual(self.item.agenda, self.agenda)
        self.assertEqual(self.item.item_type, AgendaItem.TYPE_RESOLUTION)

    def test_resolution_item_delete_keeps_resolution(self):
        """Deleting a resolution TOP does not delete the linked resolution."""
        delete_url = reverse("agendas:item_delete", kwargs={"pk": self.item.pk})

        delete_response = self.client.post(delete_url)

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(AgendaItem.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(Resolution.objects.filter(pk=self.resolution.pk).exists())

    def test_regular_item_permissions_do_not_allow_resolution_item_update(self):
        """Regular TOP edit permissions must not allow resolution TOP updates."""
        role = self._create_role(
            "REGULAR_TOP_EDITOR",
            ["agenda.edit_item_regular"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse("agendas:item_update", kwargs={"pk": self.item.pk}),
            {
                "title": "Unerlaubte Änderung",
                "description": "Nicht erlaubt",
                "parent": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Beschluss-Titel")
        self.assertEqual(self.item.description, "Beschlussbeschreibung")

    def test_regular_item_permissions_do_not_allow_resolution_item_delete(self):
        """Regular TOP delete permissions must not allow resolution TOP deletion."""
        role = self._create_role(
            "REGULAR_TOP_DELETER",
            ["agenda.delete_item_regular"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse("agendas:item_delete", kwargs={"pk": self.item.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AgendaItem.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(Resolution.objects.filter(pk=self.resolution.pk).exists())

    def test_meeting_detail_hides_resolution_items_without_resolution_view(self):
        """Meeting detail must not leak resolution TOPs without resolution.view."""
        role = self._create_role(
            "MEETING_AGENDA_VIEWER",
            ["meeting.view", "agenda.view"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.get(
            reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Beschluss-Titel")

    def test_meeting_detail_uses_linked_resolution_committee_for_visibility(self):
        """Main meeting must not leak subcommittee resolutions without subcommittee rights."""
        subcommittee = SubcommitteeFactory.create(
            parent=self.committee,
            can_create_resolutions=True,
        )
        sub_resolution = Resolution.objects.create(
            committee=subcommittee,
            title="Vertraulicher Ausschuss-Beschluss",
            description="Vertrauliche Beschreibung",
            created_by=self.user,
            status="PROPOSED",
            propose_to_main_committee=True,
        )
        sub_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title="Vertraulicher Ausschuss-Beschluss",
            description="Nicht sichtbar",
            sort_order=2,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        sub_resolution.agenda_items.create(agenda_item=sub_item)
        role = self._create_role(
            "MAIN_RESOLUTION_VIEWER",
            ["meeting.view", "agenda.view", "resolution.view"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.get(
            reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beschluss-Titel")
        self.assertNotContains(response, "Vertraulicher Ausschuss-Beschluss")

    def test_resolution_item_permission_allows_resolution_item_parent_update_only(self):
        """The dedicated resolution TOP edit permission does not allow text edits."""
        role = self._create_role(
            "RESOLUTION_TOP_EDITOR",
            ["agenda.edit_item_resolution"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse("agendas:item_update", kwargs={"pk": self.item.pk}),
            {
                "title": "Erlaubte Änderung",
                "description": "Erlaubt",
                "parent": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Beschluss-Titel")
        self.assertEqual(self.item.description, "Beschlussbeschreibung")

    def test_resolution_item_permission_allows_resolution_item_delete(self):
        """The dedicated resolution TOP delete permission deletes only the TOP link."""
        role = self._create_role(
            "RESOLUTION_TOP_DELETER",
            ["agenda.delete_item_resolution"],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse("agendas:item_delete", kwargs={"pk": self.item.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AgendaItem.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(Resolution.objects.filter(pk=self.resolution.pk).exists())
