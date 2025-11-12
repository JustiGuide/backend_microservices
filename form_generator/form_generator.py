from __future__ import annotations
import os
import shutil
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import (
    DictionaryObject,
    NameObject,
    ArrayObject,
    NumberObject,
    TextStringObject,
    BooleanObject,
    IndirectObject,
)
import re
import json
import uuid
import pathlib
from typing import List, Optional, Dict, Any, Tuple, Literal, Union, Set, Annotated
from dotenv import load_dotenv
import fitz
from openai import OpenAI
from pydantic import BaseModel, Field, ConfigDict
import base64
import time

load_dotenv()


# class FormList:
#     forms = os.listdir(os.path.dirname("./base_forms/"))
#     forms = [
#         f.split(".")[0]
#         for f in forms
#         if f.endswith(".pdf")
#         and not os.path.exists(
#             f"./gen_forms/{f.split('.')[0]}/{f.split('.')[0]}_template.pdf"
#         )
#     ]
#     forms.sort()

#     @classmethod
#     def get_forms(
#         cls, sorting_key: Literal["name", "pages"] = "pages"
#     ) -> List[Dict[str, Union[str, int]]]:
#         form_info = []
#         is_reverse = sorting_key == "pages"
#         for form in cls.forms:
#             pdf_path = os.path.join("./base_forms/", f"{form}.pdf")
#             doc = fitz.open(pdf_path)
#             page_count = len(doc)
#             doc.close()
#             form_info.append({"name": form, "pages": page_count})
#         return sorted(form_info, key=lambda x: x[sorting_key], reverse=is_reverse)


CanonicalName = Annotated[
    str,
    Field(pattern=r"^[a-z0-9_]+(?:\.[a-z0-9_]+)*\.(text|textbox|radio|checkbox|sign)$"),
]


JsonScalar = Union[str, int, float, bool]
JsonList = List[JsonScalar]
JsonValue = Union[JsonScalar, JsonList]


def timestamp_to_string(time_delta: float) -> str:
    if time_delta < 1.0:
        return f"{time_delta * 1000:.0f} ms"
    elif time_delta < 60.0:
        return f"{time_delta:.2f} sec"
    elif time_delta < 3600.0:
        return f"{time_delta / 60.0:.2f} min"
    else:
        return f"{time_delta / 3600.0:.2f} hr"


class CondExpr(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when_field: str
    op: Literal[
        "equals",
        "not_equals",
        "in",
        "not_in",
        "exists",
        "not_exists",
        "truthy",
        "falsy",
    ]
    value: Union[JsonValue, None]


class RepeatGroupCtx(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_path: Optional[str] = None
    index_strategy: Optional[
        Literal["align_by_dates", "align_by_matching_name", "append"]
    ] = "append"
    min_items: Optional[int] = 0
    max_items: Optional[int] = 0
    group_key_fields: Optional[List[str]] = None


class ValueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: str
    pattern: Union[str, None] = None
    min_length: Union[int, None] = None
    max_length: Union[int, None] = None
    allowed_values: Union[list[JsonScalar], None] = None  # <-- no Any
    normalizers: Union[list[str], None] = None
    dedupe_rule: Union[
        Literal[
            "exact",
            "case_insensitive",
            "digits_only",
            "email_canonical",
            "address_loose",
            "date_equivalent",
        ],
        None,
    ] = None


class ExtractionHints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    priority_sources: Optional[List[str]] = None
    hard_cues: Optional[List[str]] = None
    soft_cues: Optional[List[str]] = None
    regexes: Optional[List[str]] = None
    negation_cues: Optional[List[str]] = None
    disambiguation: Optional[List[str]] = None
    example_values: Optional[List[str]] = None


class QARule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule: str
    severity: Literal["error", "warn", "info"]


class SecurityCtx(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pii: Literal["none", "low", "moderate", "high"] = "moderate"
    redact_in_logs: bool = True


class ProvenanceCtx(BaseModel):
    model_config = ConfigDict(extra="forbid")
    store_file_ref: bool = True
    store_pages: bool = True
    store_confidence: bool = True


class GroupMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_group_member: bool = False
    base_path: Optional[str] = None
    selection_kind: Optional[Literal["radio_exactly_one", "checkbox_zero_plus"]] = None
    all_members: Optional[List[str]] = None


class FieldContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_name: str
    type: Literal["text", "textbox", "radio", "checkbox", "sign"]
    description: str
    required: Optional[bool] = None
    required_if: Optional[List[CondExpr]] = None
    same_as: Optional[List[str]] = None
    populate_if_missing_from: Optional[List[str]] = None
    repeat_group: Optional[RepeatGroupCtx] = None
    options: Optional[List[str]] = None
    option_source: Optional[str] = None
    value_spec: ValueSpec
    extraction: Optional[ExtractionHints] = None
    post_processing: Optional[List[str]] = None
    qa_rules: Optional[List[QARule]] = None
    security: Optional[SecurityCtx] = None
    provenance: Optional[ProvenanceCtx] = None
    group: Optional[GroupMeta] = None


class FieldContextBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: List[FieldContext]


class ChoiceItem(BaseModel):
    model_config = {"extra": "forbid"}
    label: Optional[str] = None
    canonical_key: str


class FieldMapping(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    page: int
    orig_name: str
    proposed_canonical_name: CanonicalName
    control_type: Literal["text", "textbox", "radio", "checkbox", "sign"]
    explain: Optional[str] = None
    normalized_label: Optional[str] = None
    recommend_other_text: Optional[bool] = None
    choice_map: Optional[List[ChoiceItem]] = None
    ai_extracted_option: Optional[str] = (
        None  # Pre-computed AI option for radio/checkbox fields
    )


class FieldMappingBatch(BaseModel):
    model_config = {"extra": "forbid"}
    items: List[FieldMapping]


class UnifiedFieldAnalysis(BaseModel):
    """Simplified unified field analysis for OpenAI structured output"""

    model_config = ConfigDict(extra="forbid")

    # Core field information (required)
    field_id: str
    page: int
    orig_name: str
    control_type: Literal["text", "textbox", "radio", "checkbox", "sign"]

    # Simplified canonical name (as string instead of complex object)
    canonical_name: str

    # Basic field mapping details
    explain: Optional[str] = None
    normalized_label: Optional[str] = None
    recommend_other_text: Optional[bool] = None

    # Simplified choice mapping (as list of strings instead of complex objects)
    choice_options: Optional[List[str]] = None
    ai_extracted_option: Optional[str] = (
        None  # Pre-computed AI option for radio/checkbox fields
    )

    # Basic field context
    description: str
    required: Optional[bool] = None

    # Simplified validation
    validation_passed: bool = True
    validation_errors: Optional[List[str]] = None


class UnifiedPageAnalysis(BaseModel):
    """Simplified analysis results for a single page"""

    model_config = ConfigDict(extra="forbid")
    page_number: int
    fields: List[UnifiedFieldAnalysis]


class UnifiedFormAnalysis(BaseModel):
    """Simplified complete form analysis results"""

    model_config = ConfigDict(extra="forbid")
    form_name: str
    pages: List[UnifiedPageAnalysis]


class USCIS_Unlocker:
    READONLY_BIT = 1
    CHOICE_FLAG_BITS = (
        (1 << 17) | (1 << 18) | (1 << 19) | (1 << 21) | (1 << 22) | (1 << 26)
    )

    def __init__(self, form_name: str):
        self.form_name = form_name
        self.src = f"./base_forms/{self.form_name}.pdf"
        self.dst = f"./{self.form_name}_unlocked.pdf"

    def _resolve(self, o):
        return o.get_object() if isinstance(o, IndirectObject) else o

    def _collect_widgets(
        self, page
    ) -> List[Tuple[Optional[IndirectObject], DictionaryObject]]:
        out: List[Tuple[Optional[IndirectObject], DictionaryObject]] = []
        annots = self._resolve(page.get("/Annots")) or []
        for annot_ref in annots:
            a = self._resolve(annot_ref)
            if a.get("/Subtype") == "/Widget":
                out.append(
                    (annot_ref if isinstance(annot_ref, IndirectObject) else None, a)
                )
        return out

    def _get_inherited(self, field_dict: DictionaryObject, key: str):
        cur = field_dict
        hops = 0
        while isinstance(cur, DictionaryObject) and hops < 64:
            val = cur.get(key)
            if val is not None:
                return val
            parent = cur.get("/Parent")
            cur = self._resolve(parent) if parent is not None else None
            hops += 1
        return None

    def _stringify_choice_value(self, val) -> Optional[TextStringObject]:
        if val is None:
            return None
        val = self._resolve(val)
        if isinstance(val, TextStringObject):
            return TextStringObject(str(val))
        if isinstance(val, NameObject):
            s = str(val)
            return TextStringObject(s[1:] if s.startswith("/") else s)
        if isinstance(val, ArrayObject):
            parts = []
            for item in val:
                item = self._resolve(item)
                if isinstance(item, TextStringObject):
                    parts.append(str(item))
                elif isinstance(item, NameObject):
                    s = str(item)
                    parts.append(s[1:] if s.startswith("/") else s)
                else:
                    parts.append(str(item))
            return TextStringObject(", ".join(parts))
        return TextStringObject(str(val))

    def _choice_value_from_index(
        self,
        field_dict: DictionaryObject,
    ) -> Optional[TextStringObject]:
        I = self._resolve(field_dict.get("/I"))
        Opt = self._resolve(field_dict.get("/Opt"))
        if not isinstance(I, (ArrayObject, list)) or not Opt:
            return None
        try:
            idx = int(self._resolve(I[0]))
            entry = self._resolve(Opt[idx])
            if isinstance(entry, ArrayObject) and len(entry) >= 2:
                disp = self._resolve(entry[1])
                return TextStringObject(str(disp))
            else:
                return TextStringObject(str(entry))
        except Exception:
            return None

    def _strip_widget_appearance(self, widget: DictionaryObject):
        if "/AP" in widget:
            del widget[NameObject("/AP")]

    def _ensure_acroform(self, writer: PdfWriter):
        root = writer._root_object
        acro = self._resolve(root.get("/AcroForm"))
        if not isinstance(acro, DictionaryObject):
            acro = DictionaryObject()
            root[NameObject("/AcroForm")] = writer._add_object(acro)

        if "/XFA" in acro:
            try:
                del acro[NameObject("/XFA")]
            except Exception:
                pass

        fields = self._resolve(acro.get("/Fields"))
        if not isinstance(fields, ArrayObject):
            fields = ArrayObject()
            acro[NameObject("/Fields")] = fields

        if "/NeedAppearances" not in acro:
            acro[NameObject("/NeedAppearances")] = BooleanObject(True)

        if "/DA" not in acro:
            acro[NameObject("/DA")] = TextStringObject("/Helv 12 Tf 0 g")

        if "/DR" not in acro:
            helv = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                    NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                }
            )
            helv_ref = writer._add_object(helv)
            fonts = DictionaryObject({NameObject("/Helv"): helv_ref})
            acro[NameObject("/DR")] = DictionaryObject({NameObject("/Font"): fonts})

        return acro, fields

    def _clear_readonly_everywhere(self, field_or_widget: DictionaryObject):
        cur = field_or_widget
        seen: Set[int] = set()
        while isinstance(cur, DictionaryObject):
            ff = cur.get("/Ff")
            if ff is not None:
                cur[NameObject("/Ff")] = NumberObject(int(ff) & ~self.READONLY_BIT)

            if "/Subtype" in cur and cur.get("/Subtype") == "/Widget":
                wff = cur.get("/Ff")
                if wff is not None:
                    cur[NameObject("/Ff")] = NumberObject(int(wff) & ~self.READONLY_BIT)

            for lk in ("/Lock", "/FieldLock"):
                if lk in cur:
                    try:
                        del cur[NameObject(lk)]
                    except Exception:
                        pass

            parent = cur.get("/Parent")
            if isinstance(parent, IndirectObject):
                if parent.idnum in seen:
                    break
                seen.add(parent.idnum)
                cur = self._resolve(parent)
            else:
                cur = self._resolve(parent) if parent is not None else None

    def _register_field(
        self, fields_array: ArrayObject, writer: PdfWriter, ref_or_dict
    ):
        if isinstance(ref_or_dict, IndirectObject):
            if ref_or_dict not in fields_array:
                fields_array.append(ref_or_dict)
        elif isinstance(ref_or_dict, DictionaryObject):
            ref = writer._add_object(ref_or_dict)
            if ref not in fields_array:
                fields_array.append(ref)

    def _convert_field_dict_to_text(self, field_dict: DictionaryObject) -> bool:
        if str(self._get_inherited(field_dict, "/FT")) != "/Ch":
            return False

        v = (
            self._stringify_choice_value(field_dict.get("/V"))
            or self._stringify_choice_value(field_dict.get("/DV"))
            or self._choice_value_from_index(field_dict)
        )

        field_dict[NameObject("/FT")] = NameObject("/Tx")
        if v is not None:
            field_dict[NameObject("/V")] = v
            field_dict[NameObject("/DV")] = v

        for k in ("/Opt", "/I", "/TI"):
            if k in field_dict:
                del field_dict[NameObject(k)]

        old_ff = int(field_dict.get("/Ff") or 0)
        new_ff = (old_ff & ~self.CHOICE_FLAG_BITS) & ~self.READONLY_BIT
        field_dict[NameObject("/Ff")] = NumberObject(new_ff)

        if self._get_inherited(field_dict, "/DA") is None:
            field_dict[NameObject("/DA")] = TextStringObject("/Helv 12 Tf 0 g")

        for kid in self._resolve(field_dict.get("/Kids")) or []:
            kd = self._resolve(kid)
            if isinstance(kd, DictionaryObject) and kd.get("/Subtype") == "/Widget":
                self._strip_widget_appearance(kd)
                self._clear_readonly_everywhere(kd)

        self._clear_readonly_everywhere(field_dict)
        return True

    def convert_and_unlock(self):
        reader = PdfReader(str(self.src))
        writer = PdfWriter()

        for p in reader.pages:
            writer.add_page(p)

        for page in writer.pages:
            annots = self._resolve(page.get("/Annots")) or []
            new_annots = ArrayObject()
            for annot in annots:
                a = self._resolve(annot)
                if isinstance(a, DictionaryObject) and a.get("/Subtype") == "/Widget":
                    field_carrier = (
                        self._resolve(a.get("/Parent")) if a.get("/Parent") else a
                    )
                    tu = None
                    if isinstance(field_carrier, DictionaryObject):
                        tu = field_carrier.get("/TU")
                    if tu is None:
                        tu = a.get("/TU")
                    if tu is not None and "BarCode" in str(self._resolve(tu)):
                        continue
                new_annots.append(annot)
            page[NameObject("/Annots")] = new_annots

        root = self._resolve(reader.trailer["/Root"])
        orig_acro = self._resolve(root.get("/AcroForm"))
        if isinstance(orig_acro, DictionaryObject):
            writer._root_object[NameObject("/AcroForm")] = writer._add_object(orig_acro)

        acro, fields_array = self._ensure_acroform(writer)

        present_ids: Set[int] = set()
        for fref in self._resolve(acro.get("/Fields")) or []:
            if isinstance(fref, IndirectObject):
                present_ids.add(fref.idnum)

        for page in writer.pages:
            for i, (widget_ref, widget) in enumerate(self._collect_widgets(page)):
                tu = widget.get("/TU")
                if tu is None:
                    parent = widget.get("/Parent")
                    tu = (
                        self._resolve(parent).get("/TU")
                        if isinstance(parent, (IndirectObject, DictionaryObject))
                        else None
                    )

                field_dict = (
                    self._resolve(widget.get("/Parent"))
                    if widget.get("/Parent")
                    else widget
                )
                self._clear_readonly_everywhere(widget)
                self._clear_readonly_everywhere(field_dict)

                if (
                    str(self._get_inherited(field_dict, "/FT") or field_dict.get("/FT"))
                    == "/Ch"
                ):
                    _ = self._convert_field_dict_to_text(field_dict)
                    self._strip_widget_appearance(widget)

                pref = widget.get("/Parent")
                if isinstance(pref, IndirectObject):
                    if pref.idnum not in present_ids:
                        fields_array.append(pref)
                        present_ids.add(pref.idnum)
                else:
                    if isinstance(widget_ref, IndirectObject):
                        if widget_ref.idnum not in present_ids:
                            fields_array.append(widget_ref)
                            present_ids.add(widget_ref.idnum)
                    else:
                        self._register_field(fields_array, writer, field_dict)

        acro[NameObject("/NeedAppearances")] = BooleanObject(True)

        with open(self.dst, "wb") as f:
            writer.write(f)


class FieldNameGenerator:
    FIELDNAME_RULESET = r"""
        Field Name Ruleset:
        1) Grammar
        Field name = section.subsection... .key .type
        Types (required last token):
        .text — single line (IDs, dates in YYYY‑MM‑DD, numbers‑as‑text)
        .textbox — multi line
        .radio — single choice (one canonical option)
        .checkbox — multi choice (array of canonical options)
        .sign — signature string
        Validator regex
        ^[a‑z0‑9_]+(?:\.[a‑z0‑9_]+)*\.(text|textbox|radio|checkbox|sign)$
        Token rules
        lowercase;
        segments: a–z 0–9 _;
        separator: .
        normalize labels → tokens: ASCII‑fold, collapse spaces, replace non‑alnum with _, trim _
        domain lexicon (examples): a‑number→a_number, uscis online account number→uscis_online_account_number, i‑94→i94
        2) Canonical section taxonomy
        Use only what the form needs; add more subsections freely.
        header (pre‑form items like G‑28 flag, agency use)
        applicant (primary filer)
        beneficiary (if distinct from applicant)
        petition (case/petition metadata; receipt numbers, categories)
        eligibility (basis/category selectors)
        immigration (status history, entries/exits)
        security (inadmissibility / yes‑no batteries)
        marriage, parents, children, relatives
        employment, education, financial
        bio (biographic descriptors)
        supporting_evidence (doc references)
        representative, interpreter, preparer, officer
        additional_information
        submission (system/meta: timestamps, tracking)
        You never encode “Part 1/2/…”—map paper parts to these semantic sections.
        3) Repeating groups
        Use 0‑based indices:
        employment.history.0.employer_name.text
        children.1.birth.date.text
        immigration.entries.0.class_of_admission.text
        4) Choice vocab
        Store canonical keys (UI maps to labels).
        Reserved keys you may allow across forms:
        yes, no, none, not_applicable, unknown, decline_to_answer, other
        For “other” write‑ins, add sibling:
        *.other_text.text
        5) Universal composites
        Names
        *.name.first.text | *.name.middle.text | *.name.family.text | *.name.suffix.text
        Addresses
        *.address.current.street.text | unit.text | city.text | state.text | zip.text | country.text
        *.address.mailing.*.text
        *.address.history.0.street.text ...
        Contact
        *.contact.phone_day.text | phone_mobile.text | email.text
        Identifiers
        *.identifiers.a_number.text
        *.identifiers.uscis_online_account_number.text
        *.identifiers.ssn.text
        *.identifiers.passport_number.text
        *.identifiers.i94_number.text
        Dates (store as text ISO)
        *.birth.date.text | *.marriage.date.text | *.entry.last.date.text
        Signatures (multi‑role, any form)
        applicant.signature.sign
        applicant.signature_date.text
        interpreter.signature.sign
        preparer.signature.sign
        representative.signature.sign
        officer.signature.sign
        6) Header/G‑28 & agency‑use (works for any form with those blocks)
        header.representative.g28_attached.radio
        header.representative.volag_number.text
        header.representative.attorney_state_bar_number.text
        header.representative.uscis_online_account_number.text
        header.agency_use.freeform.textbox
        header.agency_use.checks.checkbox
        7) Collision & specificity rules
        If two labels normalize to the same token, add a clarifier near the key:
        status_current.text vs status_on_i94.text
        As last resort, suffix _1, _2 to preserve compatibility.
        8) Validation
        Name matches regex (above).
        .radio: value ∈ configured enum for that field.
        .checkbox: each value ∈ enum; uniqueItems; allow empty only if none/not_applicable is an allowed value.
        .textbox: length limit (e.g., ≤ 20k).
        Dates in .text: must parse YYYY‑MM‑DD.
        .sign: non‑empty string.
        9) Deterministic generation algorithm
        Identify question context → choose semantic section.subsection...
        Normalize the label → key (token rules)
        Pick control type → append .text|textbox|radio|checkbox|sign
        For repeats → insert index at the correct level
        If choice field has “Other” → also emit *.other_text.text
        Example transformation
        “U.S. Social Security Number” → applicant.identifiers.ssn.text
        “Employment – Previous Employer (1) – Start Date” → employment.history.0.start_date.text
        “Eligibility Category (I‑765)” → eligibility.category.radio

        10) Radio and checkbox option naming
            For radio and checkbox fields, do not group multiple options into a single
            field. Instead, assign each widget its own canonical name by appending the
            normalized option token immediately before the .radio or .checkbox suffix.
            For example, if a mailing unit field has options “Apt”, “Ste”, and “Flr”,
            the canonical names should be:
                applicant.address.mailing.unit.apt.radio
                applicant.address.mailing.unit.ste.radio
                applicant.address.mailing.unit.flr.radio
            Avoid using choice_map for radio or checkbox fields; always embed the option
            token directly into the field name.

    """

    _CONTEXT_SYSTEM_PROMPT = """
        You are a senior forms architect and data validator.
        Given canonical field names (dot-notation ending with .text|.textbox|.radio|.checkbox|.sign),
        produce a structured context for EACH field that helps an AI:
        - know when to extract it (required/visibility),
        - where/how to find it (extraction cues),
        - how to validate/normalize it (value_spec),
        - how it relates to sibling choice widgets (group for radio/checkbox),
        - how to QA against other fields.
        Constraints:
        - Form-agnostic; do not mention paper 'Parts'.
        - Radio/checkbox follow Rule #10: each option is its own field (...<option>.radio/.checkbox).
        Mark group.base_path = path without '<option>.<type>'.
        selection_kind = 'radio_exactly_one' or 'checkbox_zero_plus'.
        - .text dates use ISO YYYY-MM-DD.
        - Descriptions 1–2 concise lines.
        - Conservative defaults; mark PII (email/SSN/signature high or moderate).
    """

    _SPEC_PRESETS: List[tuple[re.Pattern, Dict[str, Any]]] = [
        (
            re.compile(r"\b(email)\b"),
            {
                "format": "email",
                "pattern": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
                "normalizers": ["trim", "lowercase"],
                "dedupe_rule": "email_canonical",
            },
        ),
        (
            re.compile(r"\b(phone|telephone|mobile)\b"),
            {
                "format": "phone-us",
                "pattern": r"^\+?1?[-. (]*\d{3}[-. )]*\d{3}[-. ]*\d{4}$",
                "normalizers": ["trim"],
            },
        ),
        (
            re.compile(r"\b(date|dob|birth)\b"),
            {
                "format": "date-iso",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
                "normalizers": ["parse_human_date_to_iso", "validate_calendar_date"],
            },
        ),
        (
            re.compile(r"\b(ssn|social_security)\b"),
            {
                "format": "digits",
                "pattern": r"^\d{3}-?\d{2}-?\d{4}$",
                "normalizers": ["digits_only"],
                "dedupe_rule": "digits_only",
            },
        ),
        (
            re.compile(r"\b(a_number|a\-?number)\b"),
            {
                "format": "a-number",
                "pattern": r"^A?\d{7,9}$",
                "normalizers": ["uppercase", "strip_prefix_A"],
            },
        ),
        (
            re.compile(r"\b(i94)\b"),
            {"format": "i94", "pattern": r"^\d{11}$", "normalizers": ["digits_only"]},
        ),
        (
            re.compile(r"\b(zip)\b"),
            {
                "format": "us-zip",
                "pattern": r"^\d{5}(-\d{4})?$",
                "normalizers": ["trim"],
            },
        ),
        (
            re.compile(r"\b(passport)\b"),
            {"format": "passport", "normalizers": ["trim", "uppercase"]},
        ),
        (
            re.compile(r"\b(state|province)\b"),
            {"format": "us-state-or-province", "normalizers": ["trim", "uppercase"]},
        ),
    ]

    def __init__(self, form_name):
        self.form_name = form_name

    def _guess_value_spec_from_name(
        self, field_name: str, default_type: str
    ) -> ValueSpec:
        s = field_name.lower()
        for pat, spec in self._SPEC_PRESETS:
            if pat.search(s):
                return ValueSpec(
                    format=spec["format"],
                    pattern=spec.get("pattern"),
                    min_length=spec.get("min_length"),
                    max_length=spec.get("max_length"),
                    allowed_values=spec.get("allowed_values"),
                    normalizers=spec.get("normalizers"),
                    dedupe_rule=spec.get("dedupe_rule"),
                )
        if default_type == "textbox":
            return ValueSpec(format="free-text", max_length=20000, normalizers=["trim"])
        if default_type in {"radio", "checkbox"}:
            return ValueSpec(format="one-of" if default_type == "radio" else "set-of")
        if default_type == "sign":
            return ValueSpec(format="free-text", min_length=1, max_length=5000)
        return ValueSpec(format="free-text", normalizers=["trim", "collapse_spaces"])

    def _build_context_messages(
        self, payload: list[dict], include_examples: bool
    ) -> list[dict]:
        fewshot = [
            {
                "field_name": "applicant.identifiers.ssn.text",
                "type": "text",
                "description": "Applicant’s U.S. Social Security Number, if any.",
                "value_spec": {
                    "format": "digits",
                    "pattern": "^\\d{3}-?\\d{2}-?\\d{4}$",
                    "normalizers": ["digits_only"],
                    "dedupe_rule": "digits_only",
                },
                "extraction": {
                    "hard_cues": ["SSN", "Social Security"],
                    "regexes": ["\\b\\d{3}-\\d{2}-\\d{4}\\b", "\\b\\d{9}\\b"],
                },
            },
            {
                "field_name": "applicant.signature.sign",
                "type": "sign",
                "description": "Applicant’s signature payload or captured signature string.",
                "value_spec": {
                    "format": "free-text",
                    "min_length": 1,
                    "max_length": 5000,
                },
            },
        ]
        msgs = [
            {"role": "system", "content": self._CONTEXT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Return FieldContext for each of these canonical field names:",
            },
        ]
        if include_examples:
            msgs.append(
                {
                    "role": "user",
                    "content": json.dumps({"fields": payload}, ensure_ascii=False),
                }
            )
        else:
            msgs.append(
                {
                    "role": "user",
                    "content": json.dumps({"fields": payload}, ensure_ascii=False),
                }
            )
        return msgs

    def _group_base_for_choice_field(
        self, field_name: str, ftype: str
    ) -> Optional[str]:
        if ftype in {"radio", "checkbox"}:
            parts = field_name.split(".")
            if len(parts) >= 3:
                return ".".join(parts[:-2])
        return None

    def _collect_canonical_names_from_mapping(
        self,
        mapping_batch: FieldMappingBatch,
    ) -> List[str]:
        seen, out = set(), []
        for m in mapping_batch.items:
            n = m.proposed_canonical_name
            if n and n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def _render_page_images(
        self, pdf_path: str = "", dpi: int = 300
    ) -> Dict[int, Dict[str, str]]:
        doc = fitz.open(pdf_path)
        outdir = pathlib.Path(f"./{self.form_name}_pages")
        outdir.mkdir(parents=True, exist_ok=True)

        page_images: Dict[int, Dict[str, str]] = {}
        try:
            for pno in range(len(doc)):
                page = doc[pno]
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                fname = f"{self.form_name}_p{pno+1:02d}.png"
                fpath = outdir / fname
                pix.save(fpath.as_posix())

                with open(fpath, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode("ascii")
                data_url = f"data:image/png;base64,{b64}"

                page_images[pno + 1] = {"path": fpath.as_posix(), "data_url": data_url}
        finally:
            doc.close()

        return page_images

    def _group_by_page(
        self, fields: List[Dict[str, Any]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        by_page: Dict[int, List[Dict[str, Any]]] = {}
        for f in fields:
            page_num = int(f.get("page") or 0)
            if page_num not in by_page:
                by_page[page_num] = []
            by_page[page_num].append(f)
        return by_page


class TemplateGenerator:
    FF_RADIO = 1 << 15
    FF_PUSHBUTTON = 1 << 16
    VALID_NAME_RE = re.compile(
        r"^[a-z0-9_]+(?:\.[a-z0-9_]+)*\.(text|textbox|radio|checkbox|sign)$"
    )

    def __init__(self, form_name, src_pdf_path=None, timeout_config=None):
        self.form_name = form_name
        self.unlocker = USCIS_Unlocker(self.form_name)
        # Override source path if provided
        if src_pdf_path:
            self.unlocker.src = src_pdf_path

        self.name_generator = FieldNameGenerator(self.form_name)
        self.use_ai_option_extraction = True
        self.option_extraction_model = "gpt-5"
        self.field_mapping_model = "gpt-5"
        self.context_generation_model = "gpt-5"

        # Timeout configuration
        default_timeout_config = {
            "api_timeout": 300,  # 5 minutes for individual API calls
            "max_retries": 5,  # Number of retry attempts
            "batch_size": 5,  # Pages to process per batch
            "retry_delay_base": 3,  # Base delay for exponential backoff (seconds)
            "batch_pause": 5,  # Pause between batches (seconds)
        }

        if timeout_config:
            default_timeout_config.update(timeout_config)

        self.timeout_config = default_timeout_config
        print(f"Timeout configuration: {self.timeout_config}")

    def enforce_token_rules(self, s: str) -> str:
        s2 = s.lower().encode("ascii", "ignore").decode("ascii")
        s2 = re.sub(r"[^a-z0-9]+", "_", s2)
        s2 = s2.strip("_")
        s2 = re.sub(r"_+", "_", s2)
        return s2

    def _inline_right_text(
        self,
        page: fitz.Page,
        wrect: fitz.Rect,
        y_pad: float = 2.0,
        max_dx: float = 80.0,
    ) -> str:
        y0, y1 = wrect.y0 - y_pad, wrect.y1 + y_pad
        x_left = wrect.x1
        x_right = wrect.x1 + max_dx

        words = page.get_text("words")
        picked = []
        for x0, wy0, x1, wy1, text, *_ in words:
            if not text.strip():
                continue
            if (wy1 >= y0 and wy0 <= y1) and (x0 >= x_left) and (x0 <= x_right):
                picked.append((x0, wy0, text))

        if not picked:
            return ""
        picked.sort(key=lambda t: (t[1], t[0]))
        return " ".join(t[2] for t in picked).strip()

    def _is_multiline(self, flags: int) -> bool:
        MULTILINE_BIT = 4096
        try:
            wf = getattr(fitz, "WidgetFlags", None)
            if wf is not None:
                MULTILINE_BIT = getattr(wf, "MULTILINE", MULTILINE_BIT)
        except Exception:
            pass
        try:
            return bool(int(flags or 0) & int(MULTILINE_BIT))
        except Exception:
            return False

    def _btn_kind_from_flags(self, flags: int) -> Literal["radio", "checkbox", "push"]:
        if flags & self.FF_PUSHBUTTON:
            return "push"
        if flags & self.FF_RADIO:
            return "radio"
        return "checkbox"

    def _widget_type_to_ruleset_type(self, w: fitz.Widget) -> str:
        wt = (w.field_type_string or "").lower()
        flags = int(getattr(w, "field_flags", 0) or 0)

        if wt == "text":
            return "textbox" if self._is_multiline(flags) else "text"

        if wt in {"checkbox", "radiobutton", "button"} or hasattr(w, "on_state_name"):
            kind = self._btn_kind_from_flags(flags)
            if kind == "radio":
                return "radio"
            if kind == "push":
                return "text"
            return "checkbox"

        if wt in {"combobox", "listbox"}:
            return "radio"

        return "text"

    def _surrounding_text_between_fields(
        self,
        page: fitz.Page,
        widgets_sorted: List[fitz.Widget],
        idx: int,
        left_margin_pad: float = 8.0,
        vertical_pad: float = 4.0,
    ) -> str:
        curr = widgets_sorted[idx].rect
        prev_rect = widgets_sorted[idx - 1].rect if idx - 1 >= 0 else None
        next_rect = (
            widgets_sorted[idx + 1].rect if idx + 1 < len(widgets_sorted) else None
        )

        y_top = prev_rect.y1 if prev_rect else 0.0
        y_bot = next_rect.y0 if next_rect else page.rect.y1

        y_top -= vertical_pad
        y_bot += vertical_pad

        words = page.get_text("words")
        selected: List[Tuple[float, float, str]] = []
        x_right_limit = curr.x0 + left_margin_pad

        for x0, y0, x1, y1, text, *_ in words:
            if not text.strip():
                continue
            midy = (y0 + y1) / 2.0
            if y_top <= midy <= y_bot and x1 <= x_right_limit:
                selected.append((y0, x0, text))

        if not selected:
            return ""
        selected.sort(key=lambda t: (t[0], t[1]))
        return " ".join(t[2] for t in selected).strip()

    def extract_pdf_widgets(self, pdf_path: str) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        out: List[Dict[str, Any]] = []
        for pno in range(len(doc)):
            page = doc[pno]
            widgets = [w for w in page.widgets()] or []
            for idx, w in enumerate(widgets):
                try:
                    ruleset_type = self._widget_type_to_ruleset_type(w)
                    rect = list(vars(w.rect).values())
                    uscis_label = str(getattr(w, "field_label", "") or "").strip()

                    surrounding = self._surrounding_text_between_fields(
                        page, widgets, idx
                    )
                    label_tuple = (
                        (uscis_label, surrounding) if surrounding else (uscis_label,)
                    )

                    choices: Optional[List[str]] = None
                    wt = (w.field_type_string or "").lower()
                    if wt in {"checkbox", "radiobutton", "button"} or hasattr(
                        w, "on_state_name"
                    ):
                        on_val = getattr(w, "on_state_name", None)
                        if on_val:
                            choices = [on_val]

                    inline_hint = ""
                    if wt in {"checkbox", "radiobutton", "button"} or hasattr(
                        w, "on_state_name"
                    ):
                        inline_hint = self._inline_right_text(page, w.rect)

                    out.append(
                        {
                            "id": str(uuid.uuid4()),
                            "page": pno + 1,
                            "orig_name": w.field_name or "",
                            "widget_type": str(w.field_type_string).lower(),
                            "ruleset_type_guess": ruleset_type,
                            "rect": rect,
                            "label_guess": label_tuple,
                            "choices": choices,
                            "flags": int(getattr(w, "field_flags", 0) or 0),
                            "value": getattr(w, "field_value", None),
                            "inline_hint": inline_hint,
                        }
                    )
                except Exception as e:
                    out.append(
                        {
                            "id": str(uuid.uuid4()),
                            "page": pno + 1,
                            "orig_name": "(error)",
                            "error": repr(e),
                        }
                    )
        doc.close()
        return out


# Alias for backward compatibility
class UnifiedTemplateGenerator(TemplateGenerator):
    """Alias for TemplateGenerator with unified processing focus"""

    def __init__(self, form_name, src_pdf_path=None, **kwargs):
        # Optimize timeout config for production use
        timeout_config = {
            "api_timeout": 300,  # 5 minutes for individual API calls
            "max_retries": 5,  # Number of retry attempts
            "batch_size": 5,  # Pages to process per batch
            "retry_delay_base": 3,  # Base delay for exponential backoff (seconds)
            "batch_pause": 5,  # Pause between batches (seconds)
        }
        timeout_config.update(kwargs.get("timeout_config", {}))

        super().__init__(form_name, src_pdf_path, timeout_config=timeout_config)

    def unified_page_analysis(
        self,
        page_fields: List[Dict[str, Any]],
        page_num: int,
        page_image_data: Optional[str] = None,
        model: str = "gpt-5",
    ) -> UnifiedPageAnalysis:
        """
        Unified analysis that combines field mapping, context generation, and option extraction
        in a single API call to reduce token usage.
        """
        start_time = time.time()
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        # Prepare comprehensive field data
        slim_fields = []
        for f in page_fields:
            field_data = {
                "id": f.get("id", ""),
                "page": f.get("page", page_num),
                "orig_name": f.get("orig_name", ""),
                "control_type": f.get("control_type", "text"),
                "normalized_label": f.get("normalized_label", ""),
                "inline_hint": f.get("inline_hint", ""),
                "label_guess": f.get("label_guess", []),
                "rect": f.get("rect", []),
                "surrounding_text": f.get("surrounding_text", ""),
            }
            slim_fields.append(field_data)

        # Create comprehensive system prompt
        system_prompt = f"""
        You are an expert PDF form field analyzer that performs comprehensive field analysis.
        
        Your task is to analyze each field and provide:
        1. CANONICAL FIELD NAME following the ruleset
        2. BASIC FIELD DESCRIPTION for data extraction
        3. AI OPTION EXTRACTION for radio/checkbox fields
        4. SIMPLIFIED VALIDATION
        
        FIELD NAME RULESET:
        {self.name_generator.FIELDNAME_RULESET}
        
        SIMPLIFIED RESPONSE:
        For each field, provide:
        - field_id: The original field identifier
        - page: Page number  
        - orig_name: Original field name from PDF
        - canonical_name: Generated canonical name (as string, not object)
        - control_type: "text", "textbox", "radio", "checkbox", or "sign"
        - description: Brief 1-2 line description
        - explain: Brief explanation of the canonical name choice
        - validation_passed: true/false for basic validation
        
        For radio/checkbox fields, CRITICALLY IMPORTANT:
        - choice_options: Array of available choices as strings
        - ai_extracted_option: The specific option token for THIS individual field (e.g., "yes", "no", "male", "female", "apt", "ste")
        
        OPTION EXTRACTION RULES:
        - Extract the specific option from inline_hint, surrounding_text, or visual context
        - Use standard tokens: yes/no, male/female, apt/ste/flr, single/married, etc.
        - For sequential options use: option_1, option_2, option_a, option_b
        - For entity-specific fields: petitioner, beneficiary, applicant
        - Token must be lowercase, single word or underscore-separated
        - This eliminates the need for separate AI calls during field renaming
        
        Return structured data following the UnifiedPageAnalysis format with simplified fields.
        """

        # Prepare user content with image if available
        user_content = []
        if page_image_data:
            user_content.append(
                {"type": "image_url", "image_url": {"url": page_image_data}}
            )

        user_content.append(
            {
                "type": "text",
                "text": f"""
            Analyze these PDF form fields from page {page_num} and return structured JSON:
            
            {json.dumps({"fields": slim_fields}, ensure_ascii=False)}
            
            Provide comprehensive analysis following all rules above in JSON format.
            """,
            }
        )

        # Make single API call with timeout and retry logic
        max_retries = self.timeout_config["max_retries"]
        timeout = self.timeout_config["api_timeout"]
        retry_delay_base = self.timeout_config["retry_delay_base"]

        for attempt in range(max_retries):
            try:
                print(f"  API call attempt {attempt + 1}/{max_retries}...")

                # Create client with timeout
                client = OpenAI(api_key=api_key, timeout=timeout)

                completion = client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                user_content
                                if page_image_data
                                else user_content[0]["text"]
                            ),
                        },
                    ],
                    response_format=UnifiedPageAnalysis,
                    reasoning_effort="medium",  # Reduce reasoning effort to speed up
                )

                result = completion.choices[0].message.parsed
                if not result:
                    raise Exception("Failed to parse response")

                # The simplified model already has page_number, so just ensure it's set
                result.page_number = page_num

                print(f"  Successfully analyzed {len(result.fields)} fields")
                return result

            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {str(e)[:100]}...")
                if attempt == max_retries - 1:
                    print(
                        f"  All attempts failed, falling back to simplified processing"
                    )
                    break
                else:
                    # Wait before retry (exponential backoff)
                    wait_time = retry_delay_base**attempt
                    print(f"  Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

        # Fallback to simpler structured output if all attempts fail
        try:
            print("  Using fallback JSON processing...")

            # Simplified system prompt for faster processing
            simple_prompt = f"""
            You are an expert PDF form analyzer. Generate canonical field names for these form fields.
            
            Rules:
            - Use pattern: section.subsection.key.type
            - Types: .text, .textbox, .radio, .checkbox, .sign
            - Example: applicant.name.first.text
            
            Return JSON with this structure:
            {{
                "fields": [
                    {{
                        "field_id": "string",
                        "orig_name": "string", 
                        "proposed_canonical_name": "string",
                        "control_type": "text|radio|checkbox|textbox|sign",
                        "description": "string"
                    }}
                ]
            }}
            
            Process these fields: {json.dumps({"fields": slim_fields}, ensure_ascii=False)}
            """

            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": simple_prompt}],
                response_format={"type": "json_object"},
                timeout=180,  # Shorter timeout for fallback
            )

            # Validate response content before parsing
            response_content = completion.choices[0].message.content
            if not response_content or response_content.strip() == "":
                raise Exception("Empty response from API")

            raw_response = json.loads(response_content)

            # Validate JSON structure
            if not isinstance(raw_response, dict) or "fields" not in raw_response:
                raise Exception("Invalid JSON structure in response")

            # Convert to UnifiedPageAnalysis
            result = self._convert_raw_to_unified_analysis(
                raw_response, page_num, start_time
            )
            return result

        except Exception as final_error:
            print(f"  Final fallback failed: {final_error}")
            # Return minimal analysis to keep processing going
            return self._create_minimal_page_analysis(page_fields, page_num, start_time)

    def _convert_raw_to_unified_analysis(
        self, raw_response: dict, page_num: int, start_time: float
    ) -> UnifiedPageAnalysis:
        """Convert raw JSON response to UnifiedPageAnalysis format"""
        try:
            fields = []
            for field_data in raw_response.get("fields", []):
                field = UnifiedFieldAnalysis(
                    field_id=field_data.get("field_id", ""),
                    page=page_num,
                    orig_name=field_data.get("orig_name", ""),
                    canonical_name=field_data.get(
                        "proposed_canonical_name", ""
                    ),  # Use simplified name
                    control_type=field_data.get("control_type", "text"),
                    description=field_data.get("description", ""),
                    validation_passed=True,
                )
                fields.append(field)

            result = UnifiedPageAnalysis(page_number=page_num, fields=fields)
            return result

        except Exception as e:
            print(f"  Error converting raw response: {e}")
            return self._create_minimal_page_analysis([], page_num, start_time)

    def _create_minimal_page_analysis(self, page_fields, page_num, start_time):
        """Create minimal page analysis when all else fails"""
        try:
            fields = []
            for field in page_fields:
                # Create basic field mapping
                canonical_name = f"field_{field.get('field_id', 'unknown')}.text"

                field_analysis = UnifiedFieldAnalysis(
                    field_id=field.get("field_id", ""),
                    page=page_num,
                    orig_name=field.get("name", ""),
                    canonical_name=canonical_name,  # Use simplified name
                    control_type="text",
                    description="Minimal fallback field",
                    validation_passed=True,
                )
                fields.append(field_analysis)

            result = UnifiedPageAnalysis(page_number=page_num, fields=fields)
            return result

        except Exception as e:
            print(f"  Error in minimal analysis: {e}")
            # Return empty analysis as last resort
            return UnifiedPageAnalysis(page_number=page_num, fields=[])

    def _normalize_option_token(self, label: str) -> str:
        s = self.enforce_token_rules(label or "")
        if not s:
            return s

        synonyms = {
            "yes": "yes",
            "y": "yes",
            "no": "no",
            "n": "no",
            "apt": "apt",
            "apartment": "apt",
            "ste": "ste",
            "suite": "ste",
            "flr": "flr",
            "floor": "flr",
            "unit": "unit",
            "po_box": "po_box",
            "p_o_box": "po_box",
            # Gender options
            "male": "male",
            "m": "male",
            "female": "female",
            "f": "female",
            "other": "other",
            "non_binary": "non_binary",
            "nonbinary": "non_binary",
            "prefer_not_to_answer": "prefer_not_to_answer",
            "decline_to_answer": "decline_to_answer",
            # Common form options
            "not_applicable": "not_applicable",
            "n_a": "not_applicable",
            "na": "not_applicable",
            "unknown": "unknown",
            "none": "none",
        }

        parts = s.split("_")
        s3 = "_".join(parts[:3]) if parts else s
        if s3 in synonyms:
            return synonyms[s3]
        if parts and parts[0] in synonyms:
            return synonyms[parts[0]]
        return s3

    def apply_renames(
        self,
        pdf_path: str,
        mappings: List[FieldMapping],
        orig_fields: Optional[List[Dict[str, Any]]] = None,
        page_images: Optional[Dict[int, Dict[str, str]]] = None,
    ) -> Tuple[str, List[FieldMapping]]:
        id_lookup: Dict[
            str, Tuple[int, Tuple[float, float, float, float], str, str]
        ] = {}
        if orig_fields:
            for f in orig_fields:
                fid = f.get("id")
                if fid:
                    id_lookup[fid] = (
                        int(f.get("page") or 0),
                        tuple(f.get("rect") or (0.0, 0.0, 0.0, 0.0)),
                        f.get("orig_name") or "",
                        f.get("inline_hint") or "",
                    )

        by_page_name: Dict[
            Tuple[int, str],
            List[Tuple[Tuple[float, float, float, float], FieldMapping]],
        ] = {}
        # Create a deep copy of mappings to track changes
        new_mapping: List[FieldMapping] = []
        for m in mappings:
            # Create a new FieldMapping with the same data
            new_field_mapping = FieldMapping(
                id=m.id,
                page=m.page,
                orig_name=m.orig_name,
                proposed_canonical_name=m.proposed_canonical_name,
                control_type=m.control_type,
                explain=m.explain,
                normalized_label=m.normalized_label,
                recommend_other_text=m.recommend_other_text,
                choice_map=m.choice_map,
            )
            new_mapping.append(new_field_mapping)

            info = id_lookup.get(m.id)
            if info:
                p, rect, orig, _ = info
                by_page_name.setdefault((p, orig), []).append((rect, m))
            else:
                by_page_name.setdefault((m.page, m.orig_name), []).append(
                    ((0.0, 0.0, 0.0, 0.0), m)
                )

        # Create a mapping to track field name changes
        name_map = {}

        doc = fitz.open(pdf_path)
        try:
            for pno in range(len(doc)):
                page = doc[pno]

                per_name = {
                    k[1]: v[:] for k, v in by_page_name.items() if k[0] == pno + 1
                }

                widgets_by_old: Dict[str, List[fitz.Widget]] = {}
                for w in page.widgets() or []:
                    old = w.field_name or ""
                    widgets_by_old.setdefault(old, []).append(w)
                for old in widgets_by_old:
                    widgets_by_old[old].sort(key=lambda ww: (ww.rect.y0, ww.rect.x0))

                for old, widgets_list in widgets_by_old.items():
                    candidates = per_name.get(old)
                    if not candidates:
                        continue
                    csorted = sorted(candidates, key=lambda rm: (rm[0][1], rm[0][0]))

                    pair_count = min(len(widgets_list), len(csorted))
                    for i in range(pair_count):
                        w = widgets_list[i]
                        _, m = csorted[i]

                        base = m.proposed_canonical_name

                        try:
                            parts = base.split(".")
                            t = parts[-1] if parts else ""
                            if t in {"radio", "checkbox"}:
                                prefix = (
                                    ".".join(parts[:-2])
                                    if len(parts) >= 2
                                    else ".".join(parts[:-1])
                                )

                                # Use pre-computed AI option if available
                                if (
                                    hasattr(m, "ai_extracted_option")
                                    and m.ai_extracted_option
                                ):
                                    opt_tok = m.ai_extracted_option
                                    print(
                                        f"Using pre-computed AI option '{opt_tok}' for field {m.orig_name}"
                                    )
                                    base = f"{prefix}.{opt_tok}.{t}"
                                else:
                                    # Fallback: Quick normalization instead of full AI call
                                    inline_hint = ""
                                    info = id_lookup.get(m.id)
                                    if info:
                                        inline_hint = info[3]

                                    if inline_hint:
                                        opt_tok = self._normalize_option_token(
                                            inline_hint
                                        )
                                        if opt_tok:
                                            print(
                                                f"Using normalized option '{opt_tok}' for field {m.orig_name}"
                                            )
                                            base = f"{prefix}.{opt_tok}.{t}"
                                    else:
                                        # Final fallback: try from field mapping itself
                                        fallback_hint = (
                                            m.normalized_label or m.explain or ""
                                        )
                                        if fallback_hint:
                                            opt_tok = self._normalize_option_token(
                                                fallback_hint
                                            )
                                            if opt_tok:
                                                print(
                                                    f"Using fallback option '{opt_tok}' for field {m.orig_name}"
                                                )
                                                base = f"{prefix}.{opt_tok}.{t}"

                        except Exception:
                            pass

                        # Update new_mapping with the final field name (base) that will be applied
                        # This ensures fieldmap.json and context.json match the actual PDF field names
                        for new_m in new_mapping:
                            if new_m.id == m.id:
                                new_m.proposed_canonical_name = base
                                break

                        try:
                            w.read_only = False
                            original_field_name = w.field_name
                            w.field_name = base
                            w.update()

                        except Exception:
                            try:
                                w.field_name = base
                                w.update()
                            except Exception:
                                pass

                            except Exception:
                                pass

                        name_map[(pno + 1, old, tuple(w.rect))] = base

            out_pdf = f"./gen_forms/{self.form_name}/{self.form_name}_renamed.pdf"
            if not os.path.exists(f"./gen_forms/{self.form_name}/"):
                os.makedirs(f"./gen_forms/{self.form_name}/")
            doc.save(out_pdf)
        finally:
            doc.close()

        return out_pdf, new_mapping

    def unified_form_analysis(self) -> UnifiedFormAnalysis:
        """
        Unified approach that processes the entire form with minimal API calls
        while maintaining high accuracy through comprehensive single-pass analysis.
        """
        start_time = time.time()
        pdf_path = f"./{self.form_name}_unlocked.pdf"

        print(f"Starting unified form analysis for {self.form_name}...")

        # Extract PDF widgets once
        extract_start = time.time()
        fields = self.extract_pdf_widgets(pdf_path)
        extract_time = time.time() - extract_start
        print(f"Extracted {len(fields)} widgets in {timestamp_to_string(extract_time)}")

        if not fields:
            raise ValueError("No form fields found to process")

        # Group fields by page for processing
        fields_by_page = self.name_generator._group_by_page(fields)

        # Generate page images for visual analysis
        print("Generating page images for AI analysis...")
        page_images = self.name_generator._render_page_images(pdf_path, dpi=300)

        # Process each page with unified analysis (with batch processing for large forms)
        page_analyses = []

        # Batch processing for timeout prevention on large forms
        page_numbers = sorted(fields_by_page.keys())
        batch_size = self.timeout_config["batch_size"]
        batch_pause = self.timeout_config["batch_pause"]

        for batch_start in range(0, len(page_numbers), batch_size):
            batch_pages = page_numbers[batch_start : batch_start + batch_size]

            print(f"Processing batch: pages {batch_pages}")
            batch_success_count = 0

            for page_num in batch_pages:
                page_fields = fields_by_page[page_num]
                page_image_data = page_images.get(page_num, {}).get("data_url")

                try:
                    # Unified analysis for this page with timeout handling
                    page_analysis = self.unified_page_analysis(
                        page_fields=page_fields,
                        page_num=page_num,
                        page_image_data=page_image_data,
                        model=self.field_mapping_model,
                    )

                    page_analyses.append(page_analysis)
                    batch_success_count += 1

                    # Simple success reporting
                    print(
                        f"✓ Page {page_num}: {len(page_analysis.fields)} fields processed"
                    )

                except Exception as e:
                    print(f"✗ Page {page_num} failed: {str(e)[:100]}...")
                    # Continue with remaining pages instead of failing entire process
                    continue

            # Brief pause between batches to prevent rate limiting
            if batch_start + batch_size < len(page_numbers):
                print(
                    f"Batch complete ({batch_success_count}/{len(batch_pages)} pages successful). Pausing briefly..."
                )
                time.sleep(batch_pause)  # Configurable pause between batches

        # Create simplified form analysis
        total_fields = sum(len(p.fields) for p in page_analyses)
        passed_fields = sum(
            1 for p in page_analyses for f in p.fields if f.validation_passed
        )

        form_analysis = UnifiedFormAnalysis(
            form_name=self.form_name, pages=page_analyses
        )

        print(f"\n=== UNIFIED ANALYSIS COMPLETE ===")
        print(f"Total fields processed: {total_fields}")
        if total_fields > 0:
            success_rate = passed_fields / total_fields * 100
            print(
                f"Validation success rate: {passed_fields}/{total_fields} ({success_rate:.1f}%)"
            )
        else:
            print(f"Validation success rate: No fields processed")
        print(f"Processing time: {time.time() - start_time:.1f}s")
        print(f"Total processing time: {timestamp_to_string(time.time() - start_time)}")

        return form_analysis

    def generate_outputs_from_unified_analysis(
        self, form_analysis: UnifiedFormAnalysis, start_time: float = None
    ) -> Dict[str, Any]:
        """
        Generate the template PDF, context JSON, and field mapping JSON from unified analysis
        """
        print("\nGenerating final outputs...")

        # Create output directory
        output_dir = pathlib.Path(f"./gen_forms/{self.form_name}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert unified analysis to traditional formats for compatibility
        mappings = []
        contexts = []

        for page_analysis in form_analysis.pages:
            for field in page_analysis.fields:
                # Create FieldMapping from simplified field
                mapping = FieldMapping(
                    id=field.field_id,
                    page=field.page,
                    orig_name=field.orig_name,
                    proposed_canonical_name=field.canonical_name,  # Use simplified name
                    control_type=field.control_type,
                    explain=field.explain,
                    normalized_label=field.normalized_label,
                    recommend_other_text=field.recommend_other_text,
                    choice_map=[],  # Convert choice_options to choice_map if needed
                    ai_extracted_option=field.ai_extracted_option,  # Include pre-computed AI option
                )
                mappings.append(mapping)

                # Create simplified FieldContext
                context = FieldContext(
                    field_name=field.canonical_name,
                    type=field.control_type,
                    description=field.description,
                    required=field.required if field.required is not None else False,
                    value_spec=ValueSpec(format="free-text"),  # Default value spec
                )
                contexts.append(context)

        # Generate template PDF with field renames
        mapping_batch = FieldMappingBatch(items=mappings)
        pdf_path = f"./{self.form_name}_unlocked.pdf"

        # Debug: Print mapping information
        print(f"\nDEBUG: Generated {len(mappings)} field mappings")
        for i, mapping in enumerate(mappings[:3]):  # Show first 3
            print(
                f"  Mapping {i+1}: {mapping.orig_name} -> {mapping.proposed_canonical_name}"
            )

        # Extract original field data for the renaming process
        orig_fields = self.extract_pdf_widgets(pdf_path)
        print(f"DEBUG: Extracted {len(orig_fields)} original widget fields from PDF")

        # Generate page images for the renaming process
        page_images = self.name_generator._render_page_images(pdf_path, dpi=300)

        out_pdf, updated_mappings = self.apply_renames(
            pdf_path, mappings, orig_fields=orig_fields, page_images=page_images
        )

        # Save template PDF
        template_pdf = f"./gen_forms/{self.form_name}/{self.form_name}_template.pdf"
        pathlib.Path(out_pdf).replace(template_pdf)

        # Save field mapping JSON
        mapping_path = f"./gen_forms/{self.form_name}/{self.form_name}_fieldmap.json"
        with open(mapping_path, "w", encoding="utf-8") as f:
            f.write(FieldMappingBatch(items=updated_mappings).model_dump_json(indent=2))

        # Save context JSON
        context_path = f"./gen_forms/{self.form_name}/{self.form_name}_context.json"
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(FieldContextBatch(items=contexts).model_dump_json(indent=2))

        # Save unified analysis results for reference
        analysis_path = f"./gen_forms/{self.form_name}/{self.form_name}_analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as f:
            f.write(form_analysis.model_dump_json(indent=2))

        # Clean up temporary files
        if os.path.exists(f"./{self.form_name}_pages"):
            shutil.rmtree(f"./{self.form_name}_pages")
        if os.path.exists(f"./{self.form_name}_unlocked.pdf"):
            os.remove(f"./{self.form_name}_unlocked.pdf")

        # Calculate totals for simplified model
        total_fields = sum(len(p.fields) for p in form_analysis.pages)
        validated_fields = sum(
            1 for p in form_analysis.pages for f in p.fields if f.validation_passed
        )

        return {
            "template_pdf": template_pdf,
            "mapping_json": mapping_path,
            "context_json": context_path,
            "analysis_json": analysis_path,
            "count_widgets": total_fields,
            "count_validated": validated_fields,
            "processing_time": time.time() - start_time if start_time else 0,
        }

    def generate_template(self):
        """
        New unified template generation approach that minimizes API calls
        while maintaining accuracy through comprehensive analysis.
        """
        start = time.time()

        # Step 1: Unlock the PDF
        print("Unlocking form PDF...")
        self.unlocker.convert_and_unlock()
        unlock_done = time.time()
        print(f"Unlocked form in {timestamp_to_string(unlock_done - start)}")

        # Step 2: Perform unified analysis
        form_analysis = self.unified_form_analysis()

        # Step 3: Generate final outputs
        results = self.generate_outputs_from_unified_analysis(form_analysis, start)

        total_time = time.time() - start
        print(f"\n=== GENERATION COMPLETE ===")
        print(f"Template PDF: {results['template_pdf']}")
        print(f"Context JSON: {results['context_json']}")
        print(f"Mapping JSON: {results['mapping_json']}")
        print(f"Analysis JSON: {results['analysis_json']}")
        print(f"Total fields: {results['count_widgets']}")
        print(f"Validated fields: {results['count_validated']}")
        print(f"Processing time: {results['processing_time']:.1f}s")
        print(f"Total time: {timestamp_to_string(total_time)}")

        return results


# if __name__ == "__main__":
#     all_forms = FormList.get_forms()
#     print(f"Available forms:")
#     for i, form in enumerate(all_forms):
#         print(f" {i + 1}. {form['name']} (Pages: {form['pages']})")

#     form_selection = int(input("Select a form to process (number): "))
#     form_name = all_forms[form_selection - 1]["name"]

#     print("\n " + "=" * 45 + f" Selected form: {form_name.upper()} " + "=" * 45 + " ")

#     print("\n🚀 Using Unified Approach...")
#     generator = UnifiedTemplateGenerator(form_name)
#     results = generator.generate_template()

#     print("\n✅ Processing complete!")
#     if isinstance(results, dict) and "token_usage" in results:
#         print(f"💰 Token usage summary: {results['token_usage']}")
