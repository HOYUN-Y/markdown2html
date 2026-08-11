"""마크다운 → Blogger용 HTML 변환기 (프레임워크 무관).

이 패키지는 Flask/Django 어느 것도 import하지 않는다. 나중에 블로그
(django_blog_Enhanced)에 붙일 때 폴더째 옮기고 뷰에서 `convert()`만 부르면 되게
하려는 의도적인 제약이다.

    from converter import convert
    result = convert(markdown_text, image_base_url="https://blog.devprofessional.xyz")
    result.html      # 붙여넣을 HTML
    result.warnings  # 손봐야 할 것
    result.notes     # 테마 스니펫 안내 등
"""

from .blogger import ConversionResult, convert

__all__ = ["convert", "ConversionResult"]
