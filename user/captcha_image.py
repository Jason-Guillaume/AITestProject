"""
注册用图片验证码：白底、科技蓝字符、极轻噪声（无刺眼干扰线）。
基于 captcha.ImageCaptcha，削弱曲线噪声并改用淡灰点阵。
"""

from __future__ import annotations

from io import BytesIO

from PIL import ImageFilter

from captcha.image import ImageCaptcha


class CleanTechCaptcha(ImageCaptcha):
    """淡化噪声曲线，使用极少量浅灰噪点；默认白底 + 深蓝/科技蓝字符。"""

    def generate_image(self, chars: str, bg_color=None, fg_color=None):
        background = bg_color if bg_color is not None else (255, 255, 255)
        # #2563EB 主色，保证对比度
        color = fg_color if fg_color is not None else (37, 99, 235)
        im = self.create_captcha_image(chars, color, background)
        # 极轻 slate-200 点阵，避免库默认与文字同色带来的杂乱感
        self.create_noise_dots(im, (226, 232, 240), width=1, number=14)
        return im.filter(ImageFilter.SMOOTH)

    def generate(
        self,
        chars: str,
        format: str = "png",
        bg_color=None,
        fg_color=None,
    ) -> BytesIO:
        im = self.generate_image(chars, bg_color=bg_color, fg_color=fg_color)
        out = BytesIO()
        im.save(out, format=format)
        out.seek(0)
        return out
