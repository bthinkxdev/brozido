"""HTTP views for the core app; thin request parsing delegating to selectors/services."""

from __future__ import annotations

import json

from urllib.parse import urlencode
import threading
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.shortcuts import get_object_or_404

from core.forms import ContactInquiryForm
from core.page_rerender import is_htmx_request, rerender_app_shell
from catalog.models import Product
from core.seo import seo_context
from core.services import get_site_settings


def health_view(request: HttpRequest) -> HttpResponse:
    """Return a simple 200 OK for load-balancer health probes."""
    return HttpResponse("ok", content_type="text/plain")


@require_GET
def robots_txt_view(request: HttpRequest) -> HttpResponse:
    """Render robots.txt with the current absolute sitemap URL."""
    context = {"sitemap_url": request.build_absolute_uri("/sitemap.xml")}
    content = render_to_string("core/robots.txt", context)
    return HttpResponse(content, content_type="text/plain")


@require_GET
def about_us_view(request: HttpRequest) -> HttpResponse:
    """Render the static About Us page."""
    context = seo_context(
        request=request,
        title=f"{_('About Us')} | {settings.BRAND_NAME}",
        description=_("Learn about %(name)s, your one-stop destination for quality products at unbeatable prices.") % {"name": settings.BRAND_NAME},
    )
    return render(request, "core/about_us.html", context)


@require_GET
def privacy_policy_view(request: HttpRequest) -> HttpResponse:
    """Render the static Privacy Policy page."""
    context = seo_context(
        request=request,
        title=f"{_('Privacy Policy')} | {settings.BRAND_NAME}",
        description=_("Read the %(name)s privacy policy to learn how we collect and use your data.") % {"name": settings.BRAND_NAME},
    )
    context["policy_title"] = _("Privacy Policy")
    return render(request, "core/privacy_policy.html", context)


POLICY_PAGES = {
    "shipping-and-delivery": (_("Shipping & Delivery"), "core/policies/shipping.html"),
    "returns-and-refunds": (_("Returns & Refunds"), "core/policies/returns.html"),
    "cancellation-and-refunds": (_("Cancellation & Refunds"), "core/policies/cancellation.html"),
    "terms-and-conditions": (_("Terms & Conditions"), "core/policies/terms.html"),
    "payment-information": (_("Payment Information"), "core/policies/payment.html"),
    "security": (_("Security"), "core/policies/security.html"),
}


@require_GET
def policy_view(request: HttpRequest, slug: str) -> HttpResponse:
    """Render one of the fixed storefront policy pages."""
    if slug not in POLICY_PAGES:
        raise Http404("Unknown policy.")
    title, template = POLICY_PAGES[slug]
    context = seo_context(
        request=request,
        title=f"{title} | {settings.BRAND_NAME}",
        description=_("%(title)s at %(name)s.") % {"title": title, "name": settings.BRAND_NAME},
    )
    context["policy_title"] = title
    return render(request, template, context)


@require_GET
def contact_us_view(request: HttpRequest) -> HttpResponse:
    """Render the static Contact Us page with a contact form."""
    form = ContactInquiryForm()
    if request.user.is_authenticated:
        form.initial["name"] = request.user.get_full_name() or request.user.email
        form.initial["email"] = request.user.email

    context = seo_context(
        request=request,
        title=f"{_('Contact Us')} | {settings.BRAND_NAME}",
        description=_("Get in touch with %(name)s customer support.") % {"name": settings.BRAND_NAME},
    )
    context["form"] = form
    return render(request, "core/contact_us.html", context)


@require_POST
def submit_inquiry_view(request: HttpRequest) -> HttpResponse:
    """Handle contact form submissions."""
    form = ContactInquiryForm(request.POST)
    if form.is_valid():
        inquiry = form.save()
        
        site_settings = get_site_settings()
        
        #dispatch background email to vendor
        if site_settings.vendor_email:
            subject = f"New Inquiry from {inquiry.name}"
            message = (
                f"Name: {inquiry.name}\n"
                f"Email: {inquiry.email}\n"
                f"Message:\n{inquiry.message}"
            )
            
            def send_bg_email():
                #display name as the user, but actual sender as SMTP mail
                from_email_str = f'"{inquiry.name}" <{settings.DEFAULT_FROM_EMAIL}>'
                
                msg = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=from_email_str,
                    to=[site_settings.vendor_email],
                    reply_to=[inquiry.email]
                )
                try:
                    msg.send(fail_silently=True)
                except Exception:
                    pass
            threading.Thread(target=send_bg_email, daemon=True).start()

        messages.success(request, _("Your message has been sent successfully. We will get back to you soon."))
    else:
        messages.error(request, _("There was an error sending your message. Please check the form and try again."))
    
    return redirect(request.META.get("HTTP_REFERER", "core:contact-us"))


@require_GET
def faq_view(request: HttpRequest) -> HttpResponse:
    """Render the static FAQ page."""
    context = seo_context(
        request=request,
        title=f"{_('FAQ')} | {settings.BRAND_NAME}",
        description=_("Frequently asked questions about ordering, delivery, and payments at %(name)s.") % {"name": settings.BRAND_NAME},
    )
    
    from cms.models import FAQItem
    context["faqs"] = FAQItem.objects.filter(is_published=True)
    
    return render(request, "core/faq.html", context)


@require_GET
def blog_view(request: HttpRequest) -> HttpResponse:
    """Render the storefront blog page."""
    context = seo_context(
        request=request,
        title=f"{_('Blog')} | {settings.BRAND_NAME}",
        description=_("Read the latest news from %(name)s.") % {"name": settings.BRAND_NAME},
    )
    from cms.models import BlogPost
    context["blogs"] = BlogPost.objects.filter(is_published=True)
    return render(request, "core/blog.html", context)


@require_GET
def page_view(request: HttpRequest, slug: str) -> HttpResponse:
    """Render a dynamic storefront CMS page."""
    from cms.models import Page
    page = get_object_or_404(Page, slug=slug, is_published=True)
    
    context = seo_context(
        request=request,
        title=f"{page.title} | {settings.BRAND_NAME}",
        description=page.meta_description or page.title,
    )
    context["page"] = page
    return render(request, "core/page.html", context)


@require_POST
def set_currency_view(request: HttpRequest) -> HttpResponse:
    """Persist currency code to session."""
    code = request.POST.get("currency")
    if not code:
        from core.selectors import get_default_currency
        default_curr = get_default_currency()
        code = default_curr.code if default_curr else "INR"
    request.session["storefront_currency"] = code

    if not is_htmx_request(request):
        return redirect(request.META.get("HTTP_REFERER", "/"))

    return rerender_app_shell(request)


@require_POST
def set_country_view(request: HttpRequest) -> HttpResponse:
    """Persist the delivery country choice to session."""
    code = request.POST.get("country", "").strip().upper()
    request.session["storefront_country"] = code

    if not is_htmx_request(request):
        return redirect(request.META.get("HTTP_REFERER", "/"))

    return rerender_app_shell(request)


from django.core.exceptions import ValidationError
from django.views import View
from django.http import HttpResponse

from core import image_captcha

def get_client_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip

class ImageCaptchaImageView(View):
    """GET /captcha/<scope>.png — issue scoped image CAPTCHA into session."""

    http_method_names = ['get']

    def get(self, request, scope: str, *args, **kwargs):
        try:
            scope = image_captcha.normalize_scope(scope)
        except ValidationError:
            return HttpResponse('Not found', status=404, content_type='text/plain')

        ip_address = get_client_ip(request)
        if image_captcha.is_ip_locked(ip_address, scope):
            return HttpResponse(image_captcha.MSG_IP_LOCKED, status=429, content_type='text/plain')

        code = image_captcha.issue_captcha(request, scope)
        png = image_captcha.render_png(code)
        response = HttpResponse(png, content_type='image/png')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response
