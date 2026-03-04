from datetime import datetime, timezone
import json
import os
import re
from typing import Any

import requests

from app.models.schemas import AskResponse, SourceItem
from app.services.vector_store import VectorStore


class RagService:
    def __init__(self) -> None:
        self.store = VectorStore()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    def answer(self, question: str) -> AskResponse:
        detected_category = self._detect_category(question)
        hits = self.store.search(question, top_k=6, category_filter=detected_category)
        if not hits:
            hits = self.store.search(question, top_k=6)
        generated_at = datetime.now(timezone.utc).isoformat()
        if not hits:
            return AskResponse(
                summary="Base documentaire vide. Lance d'abord l'indexation RAG.",
                steps=[
                    "Ajouter des sources officielles dans backend/data/raw/sources.jsonl",
                    "Lancer le script d'indexation",
                    "Reposer la question"
                ],
                required_documents=[],
                common_mistakes=["Utiliser des sources non officielles ou non datees"],
                checklist=[
                    "Verifier que les sources sont officielles",
                    "Verifier que l'index Chroma contient des chunks"
                ],
                sources=[],
                confidence_score=0.0,
                generated_at=generated_at
            )

        first = hits[0]
        distance = first.get("distance")
        confidence_score = 0.65
        if isinstance(distance, (int, float)):
            confidence_score = max(0.0, min(1.0, 1.0 / (1.0 + float(distance))))

        passages = [str(item.get("text", "")) for item in hits if item.get("text")]
        sources = self._extract_sources(hits)

        llm_output = self._generate_grounded_answer(
            question=question,
            passages=passages,
            category=detected_category or "general"
        )
        if llm_output:
            summary = str(llm_output.get("summary", "")).strip() or self._build_summary(question, passages, len(sources))
            steps = self._clean_list(llm_output.get("steps"), fallback=self._extract_steps(passages), limit=6)
            required_docs = self._clean_list(llm_output.get("required_documents"), fallback=self._extract_documents(passages), limit=6)
            mistakes = self._clean_list(llm_output.get("common_mistakes"), fallback=self._extract_mistakes(passages), limit=5)
            checklist = self._clean_list(llm_output.get("checklist"), fallback=self._build_checklist(self._extract_steps(passages), self._extract_documents(passages)), limit=6)
        else:
            steps = self._extract_steps(passages)
            required_docs = self._extract_documents(passages)
            mistakes = self._extract_mistakes(passages)
            checklist = self._build_checklist(steps, required_docs)
            summary = self._build_summary(question, passages, len(sources))
        required_docs = self._normalize_documents(required_docs)
        required_docs = self._apply_question_specific_documents(question, required_docs)

        return AskResponse(
            summary=summary,
            steps=steps,
            required_documents=required_docs,
            common_mistakes=mistakes,
            checklist=checklist,
            sources=sources,
            confidence_score=round(confidence_score, 3),
            generated_at=generated_at
        )

    def _detect_category(self, question: str) -> str | None:
        q = question.lower()
        if any(k in q for k in ["carte d'identite", "carte d identite", "passeport", "acte de naissance", "nationalite"]):
            return "papiers_citoyennete"
        if any(k in q for k in ["casier", "tribunal", "justice", "plainte", "jugement"]):
            return "justice"
        if any(k in q for k in ["emploi", "travail", "securite sociale", "cnss", "recrutement"]):
            return "emploi_securite_sociale"
        if any(k in q for k in ["fiscal", "impot", "douane", "taxe", "foncier"]):
            return "fiscalite_foncier_douanes"
        if any(k in q for k in ["entreprise", "societe", "immatriculation", "commerce", "micro-entreprise", "micro entreprise"]):
            return "fiscalite_foncier_douanes"
        return None

    def _generate_grounded_answer(
        self,
        question: str,
        passages: list[str],
        category: str
    ) -> dict[str, Any] | None:
        if not self.openai_api_key:
            return None
        if not passages:
            return None

        context = "\n\n".join([f"PASSAGE {i+1}:\n{p[:1200]}" for i, p in enumerate(passages[:4])])
        prompt = (
            "Tu es un assistant administratif specialise Togo.\n"
            f"Type de demarche: {category}\n"
            "Tu dois repondre UNIQUEMENT a partir des passages fournis. "
            "Si une information n'apparait pas, ne l'invente pas.\n"
            "Retourne STRICTEMENT un JSON valide avec ce schema:\n"
            "{"
            "\"summary\": string, "
            "\"steps\": string[], "
            "\"required_documents\": string[], "
            "\"common_mistakes\": string[], "
            "\"checklist\": string[]"
            "}\n"
            f"QUESTION UTILISATEUR: {question}\n\n"
            f"PASSAGES:\n{context}\n"
        )
        payload = {
            "model": self.openai_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "Reponds uniquement en JSON valide."},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=45
            )
            response.raise_for_status()
            data = response.json()
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            return self._parse_json_object(text)
        except Exception:
            return None

    def _parse_json_object(self, raw: str) -> dict[str, Any] | None:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

    def _clean_list(self, value: Any, fallback: list[str], limit: int) -> list[str]:
        if isinstance(value, list):
            out = [str(v).strip() for v in value if str(v).strip()]
            if out:
                return out[:limit]
        return fallback[:limit]

    def _extract_steps(self, passages: list[str]) -> list[str]:
        verbs = ["verifier", "preparer", "remplir", "deposer", "soumettre", "suivre", "payer", "retirer"]
        picked: list[str] = []
        for text in passages:
            sentences = re.split(r"[.;:!?]\s+", text)
            for sentence in sentences:
                s = sentence.strip()
                if len(s) < 25:
                    continue
                low = s.lower()
                if any(v in low for v in verbs):
                    picked.append(s.capitalize())
                if len(picked) >= 5:
                    break
            if len(picked) >= 5:
                break
        if not picked:
            return [
                "Verifier l'eligibilite et l'autorite competente.",
                "Preparer les documents demandes.",
                "Completer le formulaire officiel.",
                "Deposer la demande et conserver le recu.",
                "Suivre le delai jusqu'au retrait."
            ]
        return picked[:5]

    def _extract_documents(self, passages: list[str]) -> list[str]:
        keys = ["piece", "identite", "justificatif", "certificat", "formulaire", "attestation", "copie"]
        docs: list[str] = []
        for text in passages:
            sentences = re.split(r"[.;:!?]\s+", text)
            for sentence in sentences:
                low = sentence.lower()
                if any(k in low for k in keys) and len(sentence.strip()) > 10:
                    docs.append(sentence.strip().capitalize())
                if len(docs) >= 5:
                    break
            if len(docs) >= 5:
                break
        if not docs:
            docs = [
                "Piece d'identite valide",
                "Formulaire officiel rempli",
                "Justificatif(s) demande(s) par l'administration"
            ]
        return docs[:5]

    def _normalize_documents(self, documents: list[str]) -> list[str]:
        noise_tokens = [
            "aller au contenu",
            "citoyens",
            "entreprises",
            "annuaire",
            "faq",
            "services en ligne",
            "voir tout"
        ]
        keep_keys = [
            "piece",
            "identite",
            "copie",
            "acte",
            "photo",
            "certificat",
            "attestation",
            "justificatif",
            "formulaire",
            "recu"
        ]
        out: list[str] = []
        seen: set[str] = set()
        for doc in documents:
            for part in re.split(r"[,/|•\-]\s*", str(doc)):
                text = part.strip()
                if not text:
                    continue
                low = text.lower()
                if any(token in low for token in noise_tokens):
                    continue
                if len(text) > 90:
                    continue
                if not any(k in low for k in keep_keys):
                    continue
                normalized = text[0].upper() + text[1:]
                if normalized.lower() in seen:
                    continue
                seen.add(normalized.lower())
                out.append(normalized)
                if len(out) >= 6:
                    break
            if len(out) >= 6:
                break
        if not out:
            out = [
                "Piece d'identite valide",
                "Extrait d'acte de naissance",
                "Photo d'identite recente",
                "Formulaire officiel rempli"
            ]
        return out[:6]

    def _apply_question_specific_documents(self, question: str, docs: list[str]) -> list[str]:
        q = question.lower()
        if "carte" in q and ("identite" in q or "identité" in q):
            return [
                "Extrait d'acte de naissance",
                "Photo d'identite recente",
                "Justificatif de domicile",
                "Formulaire officiel rempli"
            ]
        if "casier" in q:
            return [
                "Piece d'identite valide",
                "Extrait d'acte de naissance",
                "Formulaire de demande rempli",
                "Recu de paiement des frais"
            ]
        if any(k in q for k in ["entreprise", "micro-entreprise", "micro entreprise", "societe"]):
            return [
                "Piece d'identite du promoteur",
                "Nom commercial / raison sociale",
                "Description de l'activite",
                "Adresse d'exploitation",
                "Formulaire d'immatriculation"
            ]
        return docs

    def _extract_mistakes(self, passages: list[str]) -> list[str]:
        defaults = [
            "Dossier incomplet au depot",
            "Informations incoherentes dans le formulaire",
            "Document non lisible ou non valide"
        ]
        text = " ".join(passages).lower()
        mistakes: list[str] = []
        if "incomplet" in text:
            mistakes.append("Dossier incomplet")
        if "expire" in text:
            mistakes.append("Piece expiree")
        if "rejet" in text or "refus" in text:
            mistakes.append("Depot sans verifier les motifs de rejet frequents")
        if not mistakes:
            mistakes = defaults
        return mistakes[:4]

    def _build_checklist(self, steps: list[str], docs: list[str]) -> list[str]:
        out = [
            "Confirmer la procedure officielle la plus recente",
            "Verifier les frais et le delai avant de deposer"
        ]
        out.extend([f"Document: {d}" for d in docs[:2]])
        out.extend([f"Action: {s}" for s in steps[:2]])
        return out[:6]

    def _extract_sources(self, hits: list[dict]) -> list[SourceItem]:
        seen: set[str] = set()
        sources: list[SourceItem] = []
        for hit in hits:
            meta = hit.get("metadata", {}) or {}
            url = str(meta.get("url", "")).strip() or "https://service-public.gouv.tg/"
            if url in seen:
                continue
            seen.add(url)
            sources.append(
                SourceItem(
                    title=str(meta.get("title", "Source officielle Togo")),
                    url=url,
                    updated_at=str(meta.get("updated_at", "2026-03-04"))
                )
            )
            if len(sources) >= 5:
                break
        return sources

    def _build_summary(self, question: str, passages: list[str], source_count: int) -> str:
        base = f"Reponse basee sur {source_count} source(s) officielle(s) indexee(s) pour: {question}."
        if passages:
            excerpt = passages[0][:180].strip()
            return f"{base} Extrait pertinent: {excerpt}..."
        return base
