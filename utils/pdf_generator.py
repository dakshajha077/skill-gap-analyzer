import io
from datetime import datetime

def generate_skill_report(analysis: dict, user_name: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    NAVY    = colors.HexColor('#0F172A')
    BLUE    = colors.HexColor('#3B82F6')
    PURPLE  = colors.HexColor('#8B5CF6')
    GREEN   = colors.HexColor('#22C55E')
    YELLOW  = colors.HexColor('#F59E0B')
    RED     = colors.HexColor('#EF4444')
    GRAY    = colors.HexColor('#6B7280')
    LIGHT   = colors.HexColor('#F1F5F9')

    styles  = getSampleStyleSheet()

    H1 = ParagraphStyle('H1', fontSize=22, fontName='Helvetica-Bold', textColor=NAVY, spaceAfter=6, alignment=TA_CENTER)
    H2 = ParagraphStyle('H2', fontSize=14, fontName='Helvetica-Bold', textColor=BLUE, spaceBefore=16, spaceAfter=6)
    H3 = ParagraphStyle('H3', fontSize=11, fontName='Helvetica-Bold', textColor=NAVY, spaceBefore=8, spaceAfter=4)
    BODY= ParagraphStyle('BODY', fontSize=10, fontName='Helvetica', textColor=NAVY, spaceAfter=4, leading=14)
    SUB = ParagraphStyle('SUB', fontSize=9, fontName='Helvetica', textColor=GRAY, spaceAfter=3)
    CTR = ParagraphStyle('CTR', fontSize=10, fontName='Helvetica', textColor=GRAY, alignment=TA_CENTER)

    story = []

    story.append(Paragraph("SkillGap AI", H1))
    story.append(Paragraph("Skill Gap Analysis Report", ParagraphStyle('sub', fontSize=13, fontName='Helvetica', textColor=BLUE, spaceAfter=4, alignment=TA_CENTER)))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", CTR))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=16))

    score = analysis.get("overall_score", 0)
    label = analysis.get("profile_label", "")
    role  = analysis.get("job_role", "")

    summary_data = [
        ["Candidate", user_name,       "Job Role",    role],
        ["Overall Score", f"{score}%", "Profile",     label],
        ["Skills Matched", f"{analysis.get('strong_count',0)} strong + {analysis.get('moderate_count',0)} moderate",
         "Skills Missing", str(analysis.get("missing_count", 0))],
    ]
    summary_table = Table(summary_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',  (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), NAVY),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT, colors.white]),
        ('BOX',    (0,0), (-1,-1), 0.5, GRAY),
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Overall Match Score", H2))
    score_color = GREEN if score >= 70 else YELLOW if score >= 40 else RED
    bar_data = [[f"{score}% — {label}"]]
    bar = Table(bar_data, colWidths=[17*cm])
    bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), score_color),
        ('FONTNAME',  (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0,0), (-1,-1), 13),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('ALIGN',     (0,0), (-1,-1), 'CENTER'),
        ('PADDING',   (0,0), (-1,-1), 10),
        ('RADIUS',    (0,0), (-1,-1), 4),
    ]))
    story.append(bar)
    story.append(Spacer(1, 12))

    story.append(Paragraph("✅ Matched Skills", H2))
    matched = analysis.get("matched_skills", [])
    if matched:
        story.append(Paragraph(f"You have {len(matched)} skills that match this role's requirements.", BODY))
        rows = [["Your Skill", "Matches With", "Similarity", "Level"]]
        for m in matched:
            color_text = "Strong" if m["strength"] == "strong" else "Moderate"
            rows.append([m["user_skill"], m["matched_to"], f"{m['similarity']}%", color_text])
        t = Table(rows, colWidths=[4.5*cm, 5*cm, 3*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BLUE),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, LIGHT]),
            ('BOX',    (0,0), (-1,-1), 0.5, GRAY),
            ('INNERGRID',(0,0),(-1,-1), 0.25, colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No direct skill matches found.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("❌ Missing Skills", H2))
    missing = analysis.get("missing_skills", [])
    if missing:
        story.append(Paragraph(f"You are missing {len(missing)} required skills for this role.", BODY))
        rows = [["Required Skill", "Gap Score", "Priority"]]
        for i, m in enumerate(missing):
            priority = "High" if i < 5 else "Medium" if i < 10 else "Low"
            rows.append([m["skill"], f"{m['gap']}%", priority])
        t = Table(rows, colWidths=[7*cm, 4*cm, 6*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), RED),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, LIGHT]),
            ('BOX',    (0,0), (-1,-1), 0.5, GRAY),
            ('INNERGRID',(0,0),(-1,-1), 0.25, colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t)
    story.append(Spacer(1, 8))

    recs = analysis.get("recommendations", [])
    if recs:
        story.append(Paragraph("💡 Recommendations", H2))
        for i, rec in enumerate(recs, 1):
            story.append(Paragraph(f"{i}. {rec}", BODY))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Paragraph("Generated by SkillGap AI — Manav Rachna International Institute of Research and Studies", CTR))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def generate_interview_report(report: dict, profile: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    NAVY = colors.HexColor('#0F172A')
    BLUE = colors.HexColor('#2563EB')
    SKY = colors.HexColor('#38BDF8')
    PURPLE = colors.HexColor('#8B5CF6')
    GREEN = colors.HexColor('#10B981')
    AMBER = colors.HexColor('#F59E0B')
    RED = colors.HexColor('#EF4444')
    SLATE = colors.HexColor('#64748B')
    LIGHT = colors.HexColor('#F8FAFC')
    BORDER = colors.HexColor('#CBD5E1')

    styles = getSampleStyleSheet()
    title = ParagraphStyle('title', parent=styles['Heading1'], fontSize=24, leading=28, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6)
    subtitle = ParagraphStyle('subtitle', parent=styles['BodyText'], fontSize=11, leading=14, textColor=SLATE, alignment=TA_CENTER, spaceAfter=12)
    section = ParagraphStyle('section', parent=styles['Heading2'], fontSize=13, leading=16, textColor=BLUE, spaceBefore=12, spaceAfter=8)
    body = ParagraphStyle('body', parent=styles['BodyText'], fontSize=9.5, leading=13, textColor=NAVY)
    small = ParagraphStyle('small', parent=styles['BodyText'], fontSize=8.5, leading=11, textColor=SLATE)

    story = []

    story.append(Paragraph("SkillGap AI", title))
    story.append(Paragraph("Interview Session Report", ParagraphStyle('report_subtitle', parent=subtitle, textColor=BLUE, fontSize=13)))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=14))

    profile_rows = [
        ["Student Name", profile.get('name', 'Not available'), "Email", profile.get('email', 'Not available')],
        ["Phone", profile.get('phone') or 'Not added', "Location", profile.get('location') or 'Not added'],
        ["Member Since", profile.get('member_since', 'Not available'), "Session", f"#{report.get('session_id', '')}"],
    ]
    profile_table = Table(profile_rows, colWidths=[3.1 * cm, 5.0 * cm, 2.6 * cm, 6.3 * cm])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT, colors.white]),
        ('TEXTCOLOR', (0, 0), (-1, -1), NAVY),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.35, BORDER),
        ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("Student Profile", section))
    story.append(profile_table)
    story.append(Spacer(1, 10))

    stats_rows = [
        ["Category", report.get('category', 'Interview'), "Performance", report.get('performance_label', 'Average')],
        ["Good Answers", str(report.get('good_answers', 0)), "Needs Work", str(report.get('needs_work', 0))],
        ["Total Questions", str(report.get('total_questions', 0)), "Average Score", f"{report.get('avg_score', 0)}/100"],
    ]
    stats_table = Table(stats_rows, colWidths=[3.2 * cm, 4.8 * cm, 3.2 * cm, 4.8 * cm])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, LIGHT]),
        ('TEXTCOLOR', (0, 0), (-1, -1), NAVY),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('GRID', (0, 0), (-1, -1), 0.35, BORDER),
        ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(Paragraph("Session Summary", section))
    story.append(stats_table)
    story.append(Spacer(1, 10))

    category_rows = [["Category Breakdown", "Count", "Share"]]
    total_questions = max(report.get('total_questions', 0), 1)
    for item in report.get('category_breakdown', []):
        pct = round((item.get('count', 0) / total_questions) * 100)
        category_rows.append([item.get('label', ''), str(item.get('count', 0)), f"{pct}%"])
    category_table = Table(category_rows, colWidths=[9.2 * cm, 3.2 * cm, 3.2 * cm])
    category_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.35, BORDER),
        ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("Answer Breakdown", section))
    story.append(category_table)
    story.append(Spacer(1, 10))

    def build_bullet_rows(items, empty_text):
        if not items:
            return [[Paragraph(empty_text, body)]]
        return [[Paragraph(f"• {item}", body)] for item in items]

    strengths_table = Table(build_bullet_rows(report.get('strong_points', []), "No strong points recorded."), colWidths=[7.8 * cm])
    strengths_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECFDF5')),
        ('BOX', (0, 0), (-1, -1), 0.5, GREEN),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#A7F3D0')),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))

    improvements_table = Table(build_bullet_rows(report.get('weak_points', []), "No improvement notes recorded."), colWidths=[7.8 * cm])
    improvements_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF7ED')),
        ('BOX', (0, 0), (-1, -1), 0.5, AMBER),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#FED7AA')),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))

    story.append(Paragraph("Strengths and Improvements", section))
    paired_table = Table([
        [Paragraph("<b>Strengths</b>", body), Paragraph("<b>Areas to Improve</b>", body)],
        [strengths_table, improvements_table]
    ], colWidths=[8.0 * cm, 8.0 * cm])
    paired_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.4, BORDER),
        ('GRID', (0, 0), (-1, -1), 0.25, BORDER),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(paired_table)
    story.append(Spacer(1, 10))

    recommendations = report.get('job_recommendations', [])[:6]
    if recommendations:
        story.append(Paragraph("Recommended Job Roles", section))
        rec_rows = [[Paragraph(f"• {job}", body)] for job in recommendations]
        rec_table = Table(rec_rows, colWidths=[16.0 * cm])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
            ('BOX', (0, 0), (-1, -1), 0.5, SKY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#BFDBFE')),
            ('PADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 10))

    answer_rows = [["Question", "Result", "Score"]]
    for answer in report.get('answer_highlights', [])[:8]:
        answer_rows.append([
            Paragraph(answer.get('question', ''), small),
            Paragraph(answer.get('result_category', ''), small),
            Paragraph(str(answer.get('score', '')), small),
        ])
    if len(answer_rows) > 1:
        story.append(Paragraph("Question Highlights", section))
        answer_table = Table(answer_rows, colWidths=[10.6 * cm, 3.4 * cm, 2.0 * cm])
        answer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.35, BORDER),
            ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(answer_table)

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Generated by SkillGap AI — Interview Session Analytics", subtitle))

    doc.build(story)
    buf.seek(0)
    return buf.read()
