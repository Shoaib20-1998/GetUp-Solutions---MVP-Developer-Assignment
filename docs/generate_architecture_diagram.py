"""Renders the AWS architecture diagram to PNG using Pillow only -- no
headless browser, no external rendering service, no network dependency.
Run with: python3 docs/generate_architecture_diagram.py
"""

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1400, 900
BG = (255, 255, 255)
BOX_FILL = (235, 245, 255)
BOX_OUTLINE = (30, 64, 175)
GROUP_OUTLINE = (100, 116, 139)
TEXT = (15, 23, 42)
ARROW = (51, 65, 85)

img = Image.new("RGB", (WIDTH, HEIGHT), BG)
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except OSError:
    font = font_small = font_title = ImageFont.load_default()


def box(x, y, w, h, label, sublabel=None):
    draw.rectangle([x, y, x + w, y + h], fill=BOX_FILL, outline=BOX_OUTLINE, width=2)
    draw.text((x + w / 2, y + h / 2 - (10 if sublabel else 0)), label, fill=TEXT, font=font, anchor="mm")
    if sublabel:
        draw.text((x + w / 2, y + h / 2 + 14), sublabel, fill=TEXT, font=font_small, anchor="mm")


def group(x, y, w, h, label):
    draw.rectangle([x, y, x + w, y + h], outline=GROUP_OUTLINE, width=2)
    draw.text((x + 10, y + 8), label, fill=GROUP_OUTLINE, font=font_small)


def arrow(x1, y1, x2, y2, label=None):
    draw.line([x1, y1, x2, y2], fill=ARROW, width=2)
    # simple arrowhead
    import math

    angle = math.atan2(y2 - y1, x2 - x1)
    for da in (0.4, -0.4):
        ax = x2 - 12 * math.cos(angle - da)
        ay = y2 - 12 * math.sin(angle - da)
        draw.line([x2, y2, ax, ay], fill=ARROW, width=2)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        draw.text((mx, my - 12), label, fill=ARROW, font=font_small, anchor="mm")


draw.text((WIDTH / 2, 25), "Support Ticketing Portal -- AWS Architecture", fill=TEXT, font=font_title, anchor="mm")

# Browser
box(600, 60, 200, 50, "Browser")

# AWS account boundary
group(40, 140, 1320, 720, "AWS Account")

# Edge
group(70, 170, 380, 140, "Edge")
box(100, 200, 150, 60, "CloudFront", "CDN, HTTPS")
box(280, 200, 140, 60, "S3", "SPA static assets")

# Public subnet
group(70, 330, 380, 110, "Public Subnet")
box(100, 360, 320, 60, "Application Load Balancer", "TLS termination")

# Private subnet - app tier
group(70, 460, 380, 110, "Private Subnet -- App Tier")
box(100, 490, 320, 60, "ECS Fargate Service", "FastAPI containers, autoscaled")

# Private subnet - data tier
group(70, 590, 380, 110, "Private Subnet -- Data Tier")
box(100, 620, 320, 60, "RDS PostgreSQL", "Multi-AZ, automated backups")

# Right column: supporting services
box(560, 200, 220, 60, "S3", "Ticket attachments")
box(560, 300, 220, 60, "Secrets Manager", "JWT, DB, AI API key")
box(560, 400, 220, 60, "CloudWatch", "Logs, metrics, alarms")
box(560, 500, 220, 60, "ECR", "Container image registry")

# CI/CD
group(850, 170, 460, 140, "CI/CD")
box(880, 210, 400, 60, "GitHub Actions", "build, test, push, deploy")

# Arrows
arrow(700, 110, 190, 200, "HTTPS")
arrow(700, 110, 700, 355, "HTTPS /api")
arrow(175, 260, 260, 360)
arrow(260, 420, 260, 490, "")
arrow(260, 550, 260, 620, "TLS")
arrow(420, 520, 560, 230, "R/W attachments")
arrow(420, 520, 560, 330, "fetch secrets")
arrow(420, 520, 560, 430, "logs/metrics")
arrow(1080, 240, 780, 250, "deploy")
arrow(1080, 240, 780, 460)
arrow(1080, 240, 355, 230)

img.save("docs/cloud-architecture.png")
print("wrote docs/cloud-architecture.png")
