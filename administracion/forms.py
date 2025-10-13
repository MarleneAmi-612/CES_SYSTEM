from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

AdminUser = get_user_model()


class AdminLoginForm(forms.Form):
    email = forms.EmailField(label="Correo institucional")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    remember_me = forms.BooleanField(required=False, label="Recordarme (dispositivo de confianza)")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

class AdminAuthForm(AuthenticationForm):
    """
    Reetiqueta 'username' como correo y lo normaliza a minúsculas.
    """
    username = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={
            "class": "input",
            "placeholder": "correo@ces.mx",
            "autocomplete": "username",
            "required": True,
        })
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "Contraseña",
            "autocomplete": "current-password",
            "required": True,
        })
    )

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip().lower()

    # Mapear 'email' de tu plantilla al 'username' del form
    def __init__(self, request=None, *args, **kwargs):
        data = kwargs.get("data")
        if data and "email" in data and "username" not in data:
            # Copiamos el valor de email a username para que el form de Django lo entienda
            mutable = data._mutable if hasattr(data, "_mutable") else None
            try:
                if mutable is not None:
                    data._mutable = True
                data["username"] = data.get("email")
            finally:
                if mutable is not None:
                    data._mutable = mutable
        super().__init__(request, *args, **kwargs)

    class Meta:
        model = AdminUser
        fields = ("username", "password")