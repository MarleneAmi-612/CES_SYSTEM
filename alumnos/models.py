from django.db import models

class Request(models.Model):
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField()
    program = models.ForeignKey('alumnos.Program', on_delete=models.SET_NULL, null=True)
    curp = models.CharField(max_length=40, null=True, blank=True)
    rfc = models.CharField(max_length=15, null=True, blank=True)
    job_title = models.CharField(max_length=120, null=True, blank=True)
    industry = models.CharField(max_length=200, null=True, blank=True)
    business_name = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending','Pending'),('accepted','Accepted'),('rejected','Rejected')],
        default='pending'
    )
    sent_at = models.DateTimeField(auto_now_add=True)


class Program(models.Model):
    abbreviation = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    certificate_type = models.ForeignKey('administracion.CertificateType', on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.abbreviation

    
