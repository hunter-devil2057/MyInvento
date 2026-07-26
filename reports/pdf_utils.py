from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from io import BytesIO


def render_to_pdf(template_src, context_dict=None):
    if context_dict is None:
        context_dict = {}
    html = render_to_string(template_src, context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result, encoding='utf-8')
    if pdf.err:
        return None
    return result.getvalue()


def pdf_response(template_src, context_dict, filename='report.pdf'):
    pdf_content = render_to_pdf(template_src, context_dict)
    if pdf_content is None:
        return HttpResponse('PDF generation failed', status=500)
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
