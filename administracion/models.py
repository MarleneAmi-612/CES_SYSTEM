from django.db import models

class CertificateType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Template(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='templates/')
    certificate_type = models.ForeignKey(CertificateType, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now=True)


class Graduate(models.Model):
    request = models.ForeignKey('alumnos.Request', on_delete=models.CASCADE)
    program = models.ForeignKey('alumnos.Program', on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField()
    curp = models.CharField(max_length=40, null=True, blank=True)
    rfc = models.CharField(max_length=15, null=True, blank=True)
    job_title = models.CharField(max_length=120, null=True, blank=True)
    industry = models.CharField(max_length=200, null=True, blank=True)
    business_name = models.CharField(max_length=200, null=True, blank=True)
    url = models.CharField(max_length=25, unique=True)
    validity_start = models.DateField(null=True, blank=True)
    validity_end = models.DateField(null=True, blank=True)
    download_date = models.DateField(null=True, blank=True)
    diploma_file = models.FileField(upload_to='diplomas/')
    qr_image = models.ImageField(upload_to='qrs/', null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateField(auto_now_add=True)
