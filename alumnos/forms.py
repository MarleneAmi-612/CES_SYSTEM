# alumnos/forms.py
from django import forms
from .models import Program
import re
from .models_ces import Diplomado
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
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. Juan Carlos"
        })
    )
    lastname = forms.CharField(
        label="Apellidos",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ej. Pérez Gómez"
        })
    )

    # Ahora es ChoiceField (guarda ID del diplomado simulado)
    program = forms.ChoiceField(
        label="Programa cursado",
        choices=[],
        widget=forms.Select(attrs={
            "class": "select",
            "id": "id_program",
            "data-nice-select": "1",
            "autocomplete": "off",
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Cargamos TODOS los diplomados desde ces_simulacion
        diplos = (
            Diplomado.objects.using("ces")
            .all()
            .order_by("programa_full")
        )

        # Guardamos en la instancia para usar en clean_program
        self._diplos_by_id = {}
        choices = [("", "Selecciona un programa")]

        for d in diplos:
            full = (d.programa_full or "").strip()
            if not full:
                continue  # si viniera alguno vacío, lo saltamos

            self._diplos_by_id[str(d.id)] = d
            choices.append((str(d.id), full))

        self.fields["program"].choices = choices

    def clean_name(self):
        return (self.cleaned_data["name"] or "").strip()

    def clean_lastname(self):
        return (self.cleaned_data["lastname"] or "").strip()

    def clean_program(self):
        """
        Recibe el ID del Diplomado (simulación),
        lo mapea a un Program real (alumnos_program).
        Si no existe, lo crea con el certificate_type correcto.
        """
        value = (self.cleaned_data.get("program") or "").strip()
        if not value:
            raise forms.ValidationError("Selecciona un programa.")

        dipl = self._diplos_by_id.get(str(value))
        if not dipl:
            raise forms.ValidationError(
                "Programa no válido. Intenta de nuevo o contacta a soporte de CES."
            )

        abbr = (dipl.programa or "").strip()
        full = (dipl.programa_full or "").strip()

        # 1) Buscar si ya existe un Program equivalente
        prog = None
        if abbr:
            prog = Program.objects.filter(abbreviation__iexact=abbr).first()
        if not prog and full:
            prog = Program.objects.filter(name__iexact=full).first()

        # 2) Si no existe, lo creamos con certificate_type correcto
        if not prog:
            from administracion.models import CertificateType

            # Obtenemos tipos de certificado
            qs_ct = CertificateType.objects.all()
            ct_dc3 = qs_ct.filter(name__icontains="DC3").first()
            ct_cproem = qs_ct.filter(name__icontains="CPROEM").first()
            ct_any = qs_ct.first()

            # En la tabla `diplomado.constancia`: 1 = DC3, 0 = CPROEM
            if dipl.constancia == 1 and ct_dc3:
                ct_id = ct_dc3.id
            elif ct_cproem:
                ct_id = ct_cproem.id
            elif ct_any:
                ct_id = ct_any.id
            else:
                # Último fallback: por si acaso, pero en tu BD sí existen
                raise forms.ValidationError(
                    "No se encontró un tipo de certificado válido en el sistema."
                )

            prog = Program.objects.create(
                name=full or abbr or f"Programa {dipl.id}",
                abbreviation=abbr or None,
                certificate_type_id=ct_id,
                status=True,
            )

        # Devolvemos el Program (para que en la vista siga funcionando igual)
        return prog


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
