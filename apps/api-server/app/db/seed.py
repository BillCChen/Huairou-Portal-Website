from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import (
    Article,
    Banner,
    CaseStudy,
    Category,
    Institute,
    Leader,
    Page,
    RegistrationApplication,
    Role,
    SiteSetting,
    Tag,
    User,
)


ROLE_SEEDS = [
    ("super_admin", "Super Administrator", "Full access"),
    ("content_admin", "Content Administrator", "Manage content and files"),
    ("auditor", "Auditor", "Review content and registrations"),
    ("registered_user", "Registered User", "Portal user"),
    ("institute_editor", "Institute Editor", "Reserved institute maintainer"),
]


def seed_database(db: Session) -> None:
    if db.scalar(select(Role.id).limit(1)):
        return

    roles: dict[str, Role] = {}
    for code, name, description in ROLE_SEEDS:
        role = Role(code=code, name=name, description=description)
        db.add(role)
        roles[code] = role
    db.flush()

    admin = User(
        username=settings.admin_username,
        mobile="13800000000",
        email="admin@example.com",
        password_hash=hash_password(settings.admin_password),
        real_name=settings.admin_real_name,
        organization="Portal Office",
        expertise="Operations",
        status="active",
        role_id=roles["super_admin"].id,
    )
    db.add(admin)

    category_map: dict[str, Category] = {}
    for item in [
        Category(name="研究院新闻", slug="institute-news", type="article", sort_order=1),
        Category(name="通知公告", slug="announcements", type="article", sort_order=2),
        Category(name="行业资讯", slug="industry-updates", type="article", sort_order=3),
        Category(name="技术转化案例", slug="technology-transfer-case", type="case", sort_order=1),
        Category(name="平台建设案例", slug="platform-development-case", type="case", sort_order=2),
        Category(name="资料下载", slug="downloads", type="download", sort_order=1),
    ]:
        db.add(item)
        category_map[item.slug] = item
    db.flush()

    for item in [
        Tag(name="科技转化", slug="technology-transfer", type="case", color="#2563eb"),
        Tag(name="平台建设", slug="platform-development", type="case", color="#0f766e"),
        Tag(name="产学研合作", slug="industry-collaboration", type="case", color="#9333ea"),
    ]:
        db.add(item)

    db.add_all(
        [
            Banner(
                title="聚焦生命科学成果转化",
                subtitle="打造开放协同的创新门户，连接研究、产业与服务资源。",
                button_text="查看新闻动态",
                button_url="/news",
                sort_order=1,
                is_enabled=True,
            ),
            Banner(
                title="展示科研力量与创新案例",
                subtitle="以内容驱动门户更新，形成可持续维护的对外窗口。",
                button_text="浏览成功案例",
                button_url="/cases",
                sort_order=2,
                is_enabled=True,
            ),
        ]
    )

    db.add_all(
        [
            Page(
                page_key="about",
                title="关于我们",
                content_html="<p>北京怀柔科学城生命科学产业创新研究院聚焦生命科学成果转化与协同创新服务。</p>",
                status="published",
                blocks=[
                    {"type": "mission", "title": "使命愿景", "content": "推动成果转化、产业协同与人才汇聚。"},
                    {"type": "structure", "title": "治理结构", "content": "形成专业研究、协同转化和公共服务相结合的组织体系。"},
                ],
            ),
            Page(
                page_key="contact",
                title="联系我们",
                content_html="<p>北京市怀柔科学城生命科学产业创新研究院</p>",
                status="published",
            ),
            Page(
                page_key="talent",
                title="人才服务",
                content_html="<p>本页承接人才政策、职位信息与后续服务入口，当前以信息展示为主。</p>",
                status="published",
            ),
            Page(
                page_key="service",
                title="在线服务",
                content_html="<p>本页承接在线咨询、服务预约与资料下载入口，复杂流程保留后续扩展。</p>",
                status="published",
            ),
            Page(
                page_key="cooperation",
                title="产学研合作",
                content_html="<p>如需发起合作申请，请通过 research-partnership@example.com 与研究院联系，并提供合作方向、团队背景和预期资源需求。</p>",
                status="published",
            ),
        ]
    )

    db.add_all(
        [
            Leader(name="张某某", title="院长", intro="负责研究院总体发展与战略规划。", sort_order=1),
            Leader(name="李某某", title="副院长", intro="负责成果转化与平台建设工作。", sort_order=2),
            Leader(name="王某某", title="执行主任", intro="负责日常运营与对外合作。", sort_order=3),
        ]
    )

    db.add_all(
        [
            Institute(
                name="中医药现代转化研究所",
                slug="traditional-medicine",
                intro="聚焦中医药现代转化、标准化与产业化协同。",
                directions=[
                    {"title": "新药筛选", "summary": "聚焦中药活性成分与机制验证。"},
                    {"title": "标准化评价", "summary": "建设工艺与质量评价方法体系。"},
                ],
                contact={"email": "tm@example.com"},
                status="hidden",
                sort_order=1,
            ),
            Institute(
                name="微创医学转化研究所",
                slug="minimally-invasive-medicine",
                intro="围绕微创器械、临床转化与联合验证。",
                directions=[
                    {"title": "器械转化", "summary": "推进临床需求导向的技术验证。"},
                    {"title": "材料研究", "summary": "探索关键材料与工艺适配。"},
                ],
                contact={"email": "mi@example.com"},
                status="hidden",
                sort_order=2,
            ),
            Institute(
                name="脑科学与类脑智能研究所",
                slug="brain-science",
                intro="探索脑科学、神经调控和智能应用的交叉场景。",
                directions=[
                    {"title": "神经调控", "summary": "围绕临床应用场景开展验证。"},
                    {"title": "算法融合", "summary": "促进脑科学与智能算法结合。"},
                ],
                contact={"email": "brain@example.com"},
                status="hidden",
                sort_order=3,
            ),
            Institute(
                name="智慧药物研究所",
                slug="smart-drug",
                intro="聚焦药物发现、计算筛选和评价平台建设。",
                directions=[
                    {"title": "计算筛选", "summary": "提升候选分子发现效率。"},
                    {"title": "验证平台", "summary": "搭建平台化评价体系。"},
                ],
                contact={"email": "drug@example.com"},
                status="hidden",
                sort_order=4,
            ),
        ]
    )

    now = datetime.now(UTC)
    db.add_all(
        [
            Article(
                title="研究院门户网站建设启动",
                slug="portal-kickoff",
                summary="门户网站进入建设实施阶段，围绕形象展示、内容运营与服务引导开展建设。",
                content_html="<p>研究院门户网站建设已正式启动，本期重点覆盖首页、新闻、案例、关于我们、后台内容管理和注册审核能力。</p>",
                category_id=category_map["institute-news"].id,
                source="研究院办公室",
                author="宣传组",
                publish_at=now,
                status="published",
                is_top=True,
            ),
            Article(
                title="研究院发布创新合作方向",
                slug="innovation-collaboration",
                summary="围绕生命科学成果转化、平台共建和产业服务形成合作方向。",
                content_html="<p>研究院持续推动产学研合作，形成多元协同的合作机制。</p>",
                category_id=category_map["announcements"].id,
                source="研究院办公室",
                author="宣传组",
                publish_at=now,
                status="published",
            ),
        ]
    )

    db.add_all(
        [
            CaseStudy(
                title="智慧药物筛选平台合作案例",
                slug="smart-drug-platform-case",
                summary="联合合作方推进药物筛选平台落地与服务能力建设。",
                category_id=category_map["technology-transfer-case"].id,
                partner_name="示例合作企业",
                stage="产业转化",
                highlights=["平台联合建设", "验证效率提升", "服务能力可复制"],
                benefits="经济效益字段保留，默认按摘要展示。",
                content_html="<p>该案例围绕平台共建、技术协同和服务能力输出展开。</p>",
                result_blocks=[
                    {"title": "合作背景", "content": "围绕药物筛选效率提升开展联合验证。"},
                    {"title": "转化成果", "content": "形成可持续服务能力和标准化流程。"},
                ],
                publish_at=now,
                status="published",
            ),
            CaseStudy(
                title="微创诊疗器械临床转化案例",
                slug="minimally-invasive-case",
                summary="聚焦临床验证和器械转化路径打通。",
                category_id=category_map["platform-development-case"].id,
                partner_name="示例临床机构",
                stage="临床验证",
                highlights=["临床需求对接", "样机优化", "转化路径清晰"],
                benefits="对外公开范围可配置。",
                content_html="<p>该案例展示从需求提出到联合验证的过程。</p>",
                publish_at=now,
                status="published",
            ),
        ]
    )

    db.add_all(
        [
            SiteSetting(
                setting_key="site_profile",
                group_name="general",
                setting_value={
                    "site_name": "北京怀柔科学城生命科学产业创新研究院",
                    "site_subtitle": "聚焦生命科学成果转化与创新协同，服务研究、产业与人才资源对接。",
                    "contact_phone": "010-00000000",
                    "contact_email": "contact@example.com",
                    "address": "北京市怀柔科学城",
                    "icp_no": "待甲方确认",
                },
            ),
            SiteSetting(
                setting_key="home_stats",
                group_name="homepage",
                setting_value=[
                    {"label": "专业研究所", "value": "8"},
                    {"label": "合作企业", "value": "20+"},
                    {"label": "科技成果", "value": "50+"},
                    {"label": "重点项目", "value": "30+"},
                ],
            ),
            SiteSetting(
                setting_key="quick_links",
                group_name="homepage",
                setting_value=[
                    {"label": "新闻动态", "url": "/news"},
                    {"label": "成功案例", "url": "/cases"},
                    {"label": "人才服务", "url": "/talent"},
                    {"label": "在线服务", "url": "/service"},
                ],
            ),
            SiteSetting(
                setting_key="seo_defaults",
                group_name="seo",
                setting_value={
                    "seo_title": "北京怀柔科学城生命科学产业创新研究院",
                    "seo_desc": "聚焦生命科学成果转化与创新协同，服务研究、产业与人才资源对接。",
                    "seo_keywords": "生命科学,成果转化,研究院,科技创新",
                },
            ),
            SiteSetting(
                setting_key="footer_links",
                group_name="footer",
                setting_value={"links": []},
            ),
            SiteSetting(
                setting_key="icp_info",
                group_name="compliance",
                setting_value={"icp_no": "", "police_no": "", "analytics_code": ""},
            ),
        ]
    )

    demo_user = User(
        username="demo.user",
        mobile="13900000000",
        email="demo@example.com",
        password_hash=hash_password("DemoPass123!"),
        real_name="Demo User",
        organization="Research Partner",
        expertise="Technology Transfer",
        status="pending",
        role_id=roles["registered_user"].id,
    )
    db.add(demo_user)
    db.flush()
    db.add(RegistrationApplication(user_id=demo_user.id, review_status="pending"))

    db.commit()
