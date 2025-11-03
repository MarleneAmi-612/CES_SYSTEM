from weasyprint import HTML
HTML(string="<h1>¡Hola CES!</h1><p>PDF ok</p>").write_pdf("test_weasy.pdf")
print("Listo: test_weasy.pdf")
