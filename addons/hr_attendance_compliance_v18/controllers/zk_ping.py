from odoo import http

class ZkPingController(http.Controller):
    @http.route('/zk/ping', type='http', auth='public', csrf=False)
    def zk_ping(self, **kwargs):
        # Respuesta mínima para verificación rápida
        return http.Response('{"status":"ok"}', content_type='application/json')

    @http.route('/zk/ping_txt', type='http', auth='public', csrf=False)
    def zk_ping_txt(self, **kwargs):
        # Algunas integraciones esperan texto plano
        return http.Response('OK', content_type='text/plain')