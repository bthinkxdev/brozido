"""CMS management: homepage sections, hero slides, blog, pages, FAQs, policies."""

from __future__ import annotations

import json

from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from cms.models import (
    BlogPost,
    FAQItem,
    HeroSlide,
    HomepageSection,
    Page,
    PolicyDocument,
    SecondarySlide,
)
from cms.services import refresh_homepage_cache
from dashboard import forms
from dashboard.access import dashboard_required
from dashboard.views.base import (
    DashboardCreateView,
    DashboardDeleteView,
    DashboardListView,
    DashboardUpdateView,
)


class HomepageSectionListView(DashboardListView):
    model = HomepageSection
    nav_section = "homepage"
    url_basename = "homepagesection"
    singular_name = "Section"
    plural_name = "Homepage Sections"
    reorder_url_name = "dashboard:homepagesection-reorder"
    paginate_by = None  # the whole list must be on one page to be reordered
    default_ordering = ["display_order", "id"]
    columns = [
        {"label": "Type", "name": "get_section_type_display"},
        {"label": "Title", "name": "title"},
        {"label": "Active", "name": "is_active", "type": "bool"},
    ]


class HomepageSectionCreateView(DashboardCreateView):
    model = HomepageSection
    form_class = forms.HomepageSectionForm
    nav_section = "homepage"
    url_basename = "homepagesection"
    singular_name = "Section"

    def form_valid(self, form):
        """New sections join the end of the homepage; staff drag them into place afterwards."""
        last = HomepageSection.objects.aggregate(last=Max("display_order"))["last"]
        form.instance.display_order = (last or 0) + 1
        return super().form_valid(form)


class HomepageSectionUpdateView(DashboardUpdateView):
    model = HomepageSection
    form_class = forms.HomepageSectionForm
    nav_section = "homepage"
    url_basename = "homepagesection"
    singular_name = "Section"


class HomepageSectionDeleteView(DashboardDeleteView):
    model = HomepageSection
    nav_section = "homepage"
    url_basename = "homepagesection"
    singular_name = "Section"


class HeroSlideListView(DashboardListView):
    model = HeroSlide
    nav_section = "heroslides"
    url_basename = "heroslide"
    singular_name = "Hero Slide"
    plural_name = "Hero Slides"
    columns = [
        {"label": "Image", "name": "image", "type": "image"},
        {"label": "Title", "name": "title"},
        {"label": "Order", "name": "display_order"},
        {"label": "Active", "name": "is_active", "type": "bool"},
    ]


class HeroSlideCreateView(DashboardCreateView):
    model = HeroSlide
    form_class = forms.HeroSlideForm
    nav_section = "heroslides"
    url_basename = "heroslide"
    singular_name = "Hero Slide"


class HeroSlideUpdateView(DashboardUpdateView):
    model = HeroSlide
    form_class = forms.HeroSlideForm
    nav_section = "heroslides"
    url_basename = "heroslide"
    singular_name = "Hero Slide"


class HeroSlideDeleteView(DashboardDeleteView):
    model = HeroSlide
    nav_section = "heroslides"
    url_basename = "heroslide"
    singular_name = "Hero Slide"


class SecondarySlideListView(DashboardListView):
    model = SecondarySlide
    nav_section = "secondaryslides"
    url_basename = "secondaryslide"
    singular_name = "Secondary Slide"
    plural_name = "Secondary Slides"
    columns = [
        {"label": "Image", "name": "image", "type": "image"},
        {"label": "Title", "name": "title"},
        {"label": "Order", "name": "display_order"},
        {"label": "Active", "name": "is_active", "type": "bool"},
    ]


class SecondarySlideCreateView(DashboardCreateView):
    model = SecondarySlide
    form_class = forms.SecondarySlideForm
    nav_section = "secondaryslides"
    url_basename = "secondaryslide"
    singular_name = "Secondary Slide"


class SecondarySlideUpdateView(DashboardUpdateView):
    model = SecondarySlide
    form_class = forms.SecondarySlideForm
    nav_section = "secondaryslides"
    url_basename = "secondaryslide"
    singular_name = "Secondary Slide"


class SecondarySlideDeleteView(DashboardDeleteView):
    model = SecondarySlide
    nav_section = "secondaryslides"
    url_basename = "secondaryslide"
    singular_name = "Secondary Slide"


class BlogPostListView(DashboardListView):
    model = BlogPost
    nav_section = "blog"
    url_basename = "blogpost"
    singular_name = "Blog Post"
    plural_name = "Blog Posts"
    search_fields = ["title", "slug"]
    columns = [
        {"label": "Title", "name": "title"},
        {"label": "Slug", "name": "slug"},
        {"label": "Published", "name": "is_published", "type": "bool"},
        {"label": "Publish at", "name": "publish_at", "type": "datetime"},
    ]


class BlogPostCreateView(DashboardCreateView):
    model = BlogPost
    form_class = forms.BlogPostForm
    nav_section = "blog"
    url_basename = "blogpost"
    singular_name = "Blog Post"


class BlogPostUpdateView(DashboardUpdateView):
    model = BlogPost
    form_class = forms.BlogPostForm
    nav_section = "blog"
    url_basename = "blogpost"
    singular_name = "Blog Post"


class BlogPostDeleteView(DashboardDeleteView):
    model = BlogPost
    nav_section = "blog"
    url_basename = "blogpost"
    singular_name = "Blog Post"


class PageListView(DashboardListView):
    model = Page
    nav_section = "pages"
    url_basename = "page"
    singular_name = "Page"
    plural_name = "Pages"
    search_fields = ["title", "slug"]
    columns = [
        {"label": "Title", "name": "title"},
        {"label": "Slug", "name": "slug"},
        {"label": "Published", "name": "is_published", "type": "bool"},
    ]


class PageCreateView(DashboardCreateView):
    model = Page
    form_class = forms.PageForm
    nav_section = "pages"
    url_basename = "page"
    singular_name = "Page"


class PageUpdateView(DashboardUpdateView):
    model = Page
    form_class = forms.PageForm
    nav_section = "pages"
    url_basename = "page"
    singular_name = "Page"


class PageDeleteView(DashboardDeleteView):
    model = Page
    nav_section = "pages"
    url_basename = "page"
    singular_name = "Page"


class FAQItemListView(DashboardListView):
    model = FAQItem
    nav_section = "faqs"
    url_basename = "faq"
    singular_name = "FAQ"
    plural_name = "FAQs"
    search_fields = ["question"]
    columns = [
        {"label": "Question", "name": "question"},
        {"label": "Order", "name": "display_order"},
        {"label": "Published", "name": "is_published", "type": "bool"},
    ]


class FAQItemCreateView(DashboardCreateView):
    model = FAQItem
    form_class = forms.FAQItemForm
    nav_section = "faqs"
    url_basename = "faq"
    singular_name = "FAQ"


class FAQItemUpdateView(DashboardUpdateView):
    model = FAQItem
    form_class = forms.FAQItemForm
    nav_section = "faqs"
    url_basename = "faq"
    singular_name = "FAQ"


class FAQItemDeleteView(DashboardDeleteView):
    model = FAQItem
    nav_section = "faqs"
    url_basename = "faq"
    singular_name = "FAQ"


class PolicyDocumentListView(DashboardListView):
    model = PolicyDocument
    nav_section = "pages"
    url_basename = "policy"
    singular_name = "Policy"
    plural_name = "Policy Documents"
    search_fields = ["title", "slug"]
    columns = [
        {"label": "Title", "name": "title"},
        {"label": "Type", "name": "policy_type"},
        {"label": "Published", "name": "is_published", "type": "bool"},
    ]


class PolicyDocumentCreateView(DashboardCreateView):
    model = PolicyDocument
    form_class = forms.PolicyDocumentForm
    nav_section = "pages"
    url_basename = "policy"
    singular_name = "Policy"


class PolicyDocumentUpdateView(DashboardUpdateView):
    model = PolicyDocument
    form_class = forms.PolicyDocumentForm
    nav_section = "pages"
    url_basename = "policy"
    singular_name = "Policy"


class PolicyDocumentDeleteView(DashboardDeleteView):
    model = PolicyDocument
    nav_section = "pages"
    url_basename = "policy"
    singular_name = "Policy"


@dashboard_required
@require_POST
def homepage_section_reorder(request):
    """Save a drag-and-drop ordering of the homepage sections (JSON body: {"ids": [..]})."""
    try:
        ids = [int(pk) for pk in json.loads(request.body or b"{}").get("ids", [])]
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"detail": "Invalid order."}, status=400)

    sections = {section.pk: section for section in HomepageSection.objects.all()}
    if set(ids) != set(sections) or len(ids) != len(sections):
        return JsonResponse({"detail": "The list changed; reload the page and try again."}, status=409)

    for position, pk in enumerate(ids, start=1):
        sections[pk].display_order = position
    HomepageSection.objects.bulk_update(sections.values(), ["display_order"])
    refresh_homepage_cache()
    return JsonResponse({"detail": "ok"})
