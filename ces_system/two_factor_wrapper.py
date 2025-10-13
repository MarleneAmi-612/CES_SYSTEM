from two_factor import urls as tf_urls

# Django espera app_name cuando namespacemos
app_name = "two_factor"

# two_factor.urls define su urlpatterns como un tuple (list, 'two_factor')
# Aquí lo “normalizamos” a una LISTA de URLPattern/URLResolver:
urlpatterns = tf_urls.urlpatterns[0]  # primer elemento del tuple = lista real