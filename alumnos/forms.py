# alumnos/forms.py
from django import forms
from .models import Program
import re

# --- Regex y normalizadores ---
CURP_RE = re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$")
RFC_RE  = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")


def _norm_strip(v: str) -> str:
    return (v or "").strip()


def _norm_upper(v: str) -> str:
    return _norm_strip(v).upper()


def _norm_lower(v: str) -> str:
    return _norm_strip(v).lower()


# --- Formularios ---

class EmailForm(forms.Form):
    email = forms.EmailField(
        label="Correo con el que te registraste",
        widget=forms.EmailInput(attrs={
            "class": "input input--with-icon",   # <- antes era solo "input"
            "placeholder": "tu@correo.com"
        })
    )

    def clean_email(self):
        return _norm_lower(self.cleaned_data["email"])

class BasicDataForm(forms.Form):
    name = forms.CharField(
        label="Nombre(s)",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input","placeholder": "Ej. Juan Carlos"})
    )
    lastname = forms.CharField(
        label="Apellidos",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input","placeholder": "Ej. Pérez Gómez"})
    )
    program = forms.ModelChoiceField(
        label="Programa cursado",
        queryset=Program.objects.filter(status=True).order_by("name"),
        empty_label="Selecciona un programa",
        widget=forms.Select(attrs={
            "class": "select",
            "id": "id_program",
            "data-nice-select": "1",
            "autocomplete": "off",
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].label_from_instance = (
            lambda obj: (obj.name or obj.abbreviation or f"Programa {obj.pk}")
        )
        
    def clean_name(self):
        return (self.cleaned_data["name"] or "").strip()

    def clean_lastname(self):
        return (self.cleaned_data["lastname"] or "").strip()


class ExtrasCPROEMForm(forms.Form):
    curp = forms.CharField(
        label="CURP",
        max_length=18,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. GOML000101HDFRRN09"
        })
    )

    def clean_curp(self):
        curp = _norm_upper(self.cleaned_data["curp"])
        if len(curp) != 18 or not CURP_RE.match(curp):
            raise forms.ValidationError("CURP inválida")
        return curp


class ExtrasDC3Form(forms.Form):
    curp = forms.CharField(
        label="CURP",
        max_length=18,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. GOML000101HDFRRN09"
        })
    )
    rfc = forms.CharField(
        label="RFC",
        max_length=13,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. GOMJ000101ABC"
        })
    )
    job_title = forms.CharField(
        label="Puesto",
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. Desarrollador de Software"
        })
    )
    industry = forms.CharField(
        label="Giro",
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. Tecnologías de la Información"
        })
    )
    business_name = forms.CharField(
        label="Razón social",
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. CES S.A. de C.V."
        })
    )

    def clean_curp(self):
        curp = _norm_upper(self.cleaned_data["curp"])
        if len(curp) != 18 or not CURP_RE.match(curp):
            raise forms.ValidationError("CURP inválida")
        return curp

    def clean_rfc(self):
        rfc = _norm_upper(self.cleaned_data["rfc"])
        if not RFC_RE.match(rfc):
            raise forms.ValidationError("RFC inválido")
        return rfc

    def clean_job_title(self):
        return _norm_strip(self.cleaned_data["job_title"])

    def clean_industry(self):
        return _norm_strip(self.cleaned_data["industry"])

    def clean_business_name(self):
        return _norm_strip(self.cleaned_data["business_name"])
