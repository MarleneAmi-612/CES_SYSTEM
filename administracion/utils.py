def get_client_ip(request):
    # Respeta proxies/reverse proxies
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # puede venir "ip_real, proxy1, proxy2"
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
