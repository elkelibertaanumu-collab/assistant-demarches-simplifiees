from app.models.schemas import (
    FormAssistResponse,
    FormFieldDefinition,
    FormGenerateResponse,
    FormTemplateItem
)


class FormService:
    def __init__(self) -> None:
        self.templates = self._build_templates()

    def _build_templates(self) -> dict[str, FormTemplateItem]:
        return {
            "cni_tg": FormTemplateItem(
                form_id="cni_tg",
                title="Demande Carte Nationale d'Identite (Togo)",
                fields=[
                    FormFieldDefinition(key="full_name", label="Nom et prenom(s)", placeholder="Ex: Kossi Mensah"),
                    FormFieldDefinition(key="birth_date", label="Date de naissance", placeholder="JJ/MM/AAAA"),
                    FormFieldDefinition(key="birth_place", label="Lieu de naissance", placeholder="Ex: Lome"),
                    FormFieldDefinition(key="address", label="Adresse actuelle", placeholder="Ex: Agoe, Lome"),
                    FormFieldDefinition(key="profession", label="Profession", required=False, placeholder="Ex: Etudiant")
                ]
            ),
            "casier_tg": FormTemplateItem(
                form_id="casier_tg",
                title="Demande Extrait de Casier Judiciaire (Togo)",
                fields=[
                    FormFieldDefinition(key="full_name", label="Nom et prenom(s)", placeholder="Ex: Ama K."),
                    FormFieldDefinition(key="birth_date", label="Date de naissance", placeholder="JJ/MM/AAAA"),
                    FormFieldDefinition(key="birth_place", label="Lieu de naissance", placeholder="Ex: Kara"),
                    FormFieldDefinition(key="nationality", label="Nationalite", placeholder="Ex: Togolaise"),
                    FormFieldDefinition(key="request_reason", label="Motif de la demande", placeholder="Ex: Dossier emploi")
                ]
            ),
            "micro_entreprise_tg": FormTemplateItem(
                form_id="micro_entreprise_tg",
                title="Declaration Micro-Entreprise (Togo)",
                fields=[
                    FormFieldDefinition(key="promoter_name", label="Nom du promoteur", placeholder="Ex: Yao K."),
                    FormFieldDefinition(key="business_name", label="Nom commercial", placeholder="Ex: YK Services"),
                    FormFieldDefinition(key="activity", label="Activite principale", placeholder="Ex: Commerce"),
                    FormFieldDefinition(key="business_address", label="Adresse d'exploitation", placeholder="Ex: Adidogome"),
                    FormFieldDefinition(key="phone", label="Telephone", placeholder="Ex: +228 90 00 00 00")
                ]
            )
        }

    def list_templates(self) -> list[FormTemplateItem]:
        return list(self.templates.values())

    def assist_field(self, form_id: str, field_key: str, current_values: dict[str, str]) -> FormAssistResponse:
        template = self.templates.get(form_id)
        if not template:
            return FormAssistResponse(suggestion="", tips=["Formulaire introuvable."])
        field = next((f for f in template.fields if f.key == field_key), None)
        if not field:
            return FormAssistResponse(suggestion="", tips=["Champ introuvable."])

        base = current_values.get(field_key, "").strip()
        suggestion = base if base else f"Renseigne {field.label.lower()} clairement et sans abreviation."
        tips = [
            "Utilise les memes informations que sur tes documents officiels.",
            "Evite les fautes d'orthographe dans les noms et lieux.",
            "Verifie les dates avant la soumission."
        ]
        return FormAssistResponse(suggestion=suggestion, tips=tips)

    def generate_preview(self, form_id: str, values: dict[str, str]) -> FormGenerateResponse:
        template = self.templates.get(form_id)
        if not template:
            return FormGenerateResponse(
                form_id=form_id,
                title="Formulaire non reconnu",
                values=values,
                preview_lines=[],
                disclaimer="Brouillon non officiel."
            )

        lines = [template.title, ""]
        for field in template.fields:
            value = str(values.get(field.key, "")).strip()
            lines.append(f"{field.label}: {value}")

        return FormGenerateResponse(
            form_id=form_id,
            title=template.title,
            values=values,
            preview_lines=lines,
            disclaimer="Brouillon non officiel. Verifie avec le formulaire officiel avant depot."
        )
