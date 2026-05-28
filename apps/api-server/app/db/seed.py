from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import (
    Article,
    Banner,
    CaseStudy,
    Category,
    DownloadResource,
    FileRecord,
    Institute,
    Leader,
    Page,
    RegistrationApplication,
    Role,
    ServiceRequest,
    SiteSetting,
    Tag,
    User,
)


ROLE_SEEDS = [
    ("super_admin", "超级管理员", "全量权限管理"),
    ("content_admin", "内容管理员", "管理内容与文件"),
    ("auditor", "审核管理员", "审核内容与注册信息"),
    ("registered_user", "注册用户", "门户用户"),
    ("institute_editor", "研究所管理员", "保留的研究所内容维护角色"),
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
        organization="研究院办公室",
        expertise="内容运营",
        status="active",
        role_id=roles["super_admin"].id,
    )
    db.add(admin)

    category_specs = [
        ("院内新闻", "院内新闻", "article", 1),
        ("行业资讯", "行业资讯", "article", 2),
        ("通知公告", "通知公告", "article", 3),
        ("媒体聚焦", "媒体聚焦", "article", 4),
        ("成果转化案例", "成果转化案例", "case", 1),
        ("平台建设案例", "平台建设案例", "case", 2),
        ("产学研合作案例", "产学研合作案例", "case", 3),
        ("服务指南", "服务指南", "download", 1),
        ("政策文件", "政策文件", "download", 2),
    ]
    category_map: dict[str, Category] = {}
    for name, slug, category_type, sort_order in category_specs:
        item = Category(name=name, slug=slug, type=category_type, sort_order=sort_order)
        db.add(item)
        category_map[slug] = item
    db.flush()

    for item in [
        Tag(name="院内新闻", slug="院内新闻", type="新闻", color="#0f5b78"),
        Tag(name="行业资讯", slug="行业资讯", type="新闻", color="#0f766e"),
        Tag(name="通知公告", slug="通知公告", type="新闻", color="#b45309"),
        Tag(name="媒体聚焦", slug="媒体聚焦", type="新闻", color="#7c3aed"),
        Tag(name="科技转化", slug="科技转化", type="案例", color="#2563eb"),
        Tag(name="平台建设", slug="平台建设", type="案例", color="#0f766e"),
        Tag(name="产学研合作", slug="产学研合作", type="案例", color="#9333ea"),
        Tag(name="人才服务", slug="人才服务", type="服务", color="#be123c"),
    ]:
        db.add(item)

    db.add_all(
        [
            Banner(
                title="聚焦生命科学成果转化",
                subtitle="构建研究、产业、人才和公共服务协同的展示窗口。",
                button_text="查看院内新闻",
                button_url="/?category_slug=院内新闻",
                tag="院内新闻",
                sort_order=1,
                is_enabled=True,
            ),
            Banner(
                title="共性平台开放服务",
                subtitle="围绕检测评价、实验验证和产业转化提供可预约的平台能力。",
                button_text="了解共性平台",
                button_url="/platforms",
                tag="行业资讯",
                sort_order=2,
                is_enabled=True,
            ),
            Banner(
                title="项目申报与活动通知",
                subtitle="发布政策申报、项目征集和培训活动等重要通知。",
                button_text="查看通知公告",
                button_url="/?category_slug=通知公告",
                tag="通知公告",
                sort_order=3,
                is_enabled=True,
            ),
            Banner(
                title="媒体关注怀柔生命科学创新",
                subtitle="集中呈现媒体报道、专题采访和产业观察内容。",
                button_text="查看媒体聚焦",
                button_url="/?category_slug=媒体聚焦",
                tag="媒体聚焦",
                sort_order=4,
                is_enabled=True,
            ),
        ]
    )

    page_specs = [
        (
            "about",
            "关于我们",
            "<p>北京怀柔科学城生命科学产业创新研究院围绕生命科学成果转化、共性平台建设、产业资源对接和人才服务开展工作。</p><p>研究院以开放协同为基本机制，连接高校院所、医疗机构、创新企业和公共服务资源，形成从项目发现到应用验证的转化链条。</p>",
            [
                {"type": "定位", "title": "功能定位", "content": "服务生命科学成果转化和产业协同创新。"},
                {"type": "机制", "title": "协同机制", "content": "通过项目征集、平台开放和专家服务形成常态化对接。"},
            ],
        ),
        (
            "contact",
            "联系我们",
            "<p>地址：北京市怀柔科学城生命科学产业创新研究院示范办公区。</p><p>电话：010-61660000；邮箱：contact@hru-life.example。</p>",
            [],
        ),
        (
            "talent",
            "人才服务",
            "<p>人才服务板块用于发布高层次人才政策、岗位信息、创新团队服务和活动报名入口。</p><p>示例内容包含博士后合作、产业导师对接、人才公寓咨询和科研服务包申请。</p>",
            [
                {"type": "服务", "title": "人才政策咨询", "content": "提供政策适配、材料准备和申报节点提醒。"},
                {"type": "服务", "title": "创新团队对接", "content": "面向重点项目匹配技术、产业和临床合作资源。"},
            ],
        ),
        (
            "service",
            "在线服务",
            "<p>在线服务用于承接咨询提交、服务预约、资料下载和活动报名。</p><p>当前测试数据提供平台预约、成果对接、政策咨询和培训报名四类服务说明。</p>",
            [
                {"type": "入口", "title": "平台预约", "content": "面向检测评价、实验验证和工艺放大需求收集服务申请。"},
                {"type": "入口", "title": "成果对接", "content": "面向项目方和企业方收集合作线索。"},
            ],
        ),
        (
            "cooperation",
            "产学研合作",
            "<p>产学研合作板块用于发布合作项目、联合攻关方向和活动报名信息。</p><p>测试数据示例：研究院正在征集智慧药物筛选、微创器械验证、脑科学设备评估等合作需求，合作方可通过在线服务提交意向。</p>",
            [
                {"type": "合作方向", "title": "联合攻关", "content": "围绕关键技术形成企业、高校和临床机构协同课题。"},
                {"type": "合作方向", "title": "项目路演", "content": "定期组织成果展示、需求发布和投资机构交流。"},
            ],
        ),
        (
            "incubation",
            "成果孵化",
            "<p>成果孵化板块展示在孵项目、创业服务、政策辅导和产业化进展。</p><p>测试项目覆盖细胞治疗工艺优化、智能康复设备、天然产物活性评价和临床样本数据治理。</p>",
            [
                {"type": "孵化服务", "title": "项目诊断", "content": "从技术成熟度、合规路径和市场场景三个维度形成孵化建议。"},
                {"type": "孵化服务", "title": "创业支持", "content": "提供导师辅导、政策申报和场地资源对接。"},
            ],
        ),
        (
            "platforms",
            "共性平台",
            "<p>共性平台板块展示研究院面向外部开放的实验验证、检测评价和技术服务能力。</p><p>示例平台包括合成生物学验证平台、医疗器械评价平台、实验动物服务平台和制剂工艺平台。</p>",
            [
                {"type": "平台", "title": "合成生物学验证平台", "content": "支持菌株构建、表达验证和小试评价。"},
                {"type": "平台", "title": "医疗器械评价平台", "content": "支持样机评估、临床需求分析和注册路径咨询。"},
            ],
        ),
        (
            "search-stats",
            "搜索与数据统计",
            "<p>搜索与数据统计板块用于承载全站检索、热门内容、访问趋势和业务数据展示。</p><p>测试口径包含新闻检索、案例检索、平台预约量、合作线索量和注册用户审核状态。</p>",
            [
                {"type": "能力", "title": "智能搜索", "content": "覆盖新闻、案例、研究所、平台服务和政策内容。"},
                {"type": "能力", "title": "业务统计", "content": "汇总咨询线索、服务申请、内容发布和注册审核数据。"},
            ],
        ),
        (
            "adaptation",
            "客户端适配",
            "<p>客户端适配板块用于说明门户在 PC、平板和手机端的展示策略。</p><p>测试内容覆盖首页新闻卡片、后台内容录入、表单提交和详情页阅读在多终端下的适配目标。</p>",
            [
                {"type": "终端", "title": "移动端", "content": "优先保证导航、搜索、新闻列表和咨询表单可读可用。"},
                {"type": "终端", "title": "桌面端", "content": "强化内容扫描、后台管理和列表编辑效率。"},
            ],
        ),
        (
            "systems",
            "业务系统模块",
            "<p>业务系统模块用于展示后续可对接的外部系统入口和数据共享说明。</p><p>示例系统包括成果转化资源对接系统、培训业务系统、协同办公系统和数据统计系统。</p>",
            [
                {"type": "系统", "title": "成果转化资源对接系统", "content": "承接项目线索、合作需求和资源匹配信息。"},
                {"type": "系统", "title": "培训业务系统", "content": "承接活动报名、课程发布和签到数据对接。"},
            ],
        ),
    ]
    for page_key, title, content_html, blocks in page_specs:
        db.add(Page(page_key=page_key, title=title, content_html=content_html, status="published", blocks=blocks))

    db.add_all(
        [
            Leader(name="化名甲", title="院长", intro="负责研究院总体战略、重大项目布局和开放合作机制建设。", sort_order=1),
            Leader(name="化名乙", title="副院长", intro="负责成果转化、共性平台建设和企业服务体系。", sort_order=2),
            Leader(name="化名丙", title="执行主任", intro="负责内容运营、人才服务和在线服务闭环。", sort_order=3),
            Leader(name="化名丁", title="首席科学顾问", intro="负责生命科学重点方向论证和专家资源协调。", sort_order=4),
        ]
    )

    db.add_all(
        [
            Institute(
                name="中医药现代转化研究所",
                slug="traditional-medicine",
                intro="聚焦中医药现代转化、标准化评价和产业化验证。",
                directions=[
                    {"title": "活性成分筛选", "summary": "围绕重点中药资源开展活性评价与机制验证。"},
                    {"title": "质量标准研究", "summary": "建设工艺控制、质量评价和稳定性研究体系。"},
                ],
                contact={"email": "tm@hru-life.example", "phone": "010-61660011"},
                status="published",
                sort_order=1,
            ),
            Institute(
                name="微创医学转化研究所",
                slug="minimally-invasive-medicine",
                intro="围绕微创器械、临床验证和样机优化开展转化服务。",
                directions=[
                    {"title": "器械样机评估", "summary": "支持临床需求梳理、样机测试和注册路径咨询。"},
                    {"title": "医工协同验证", "summary": "组织临床专家和工程团队开展联合验证。"},
                ],
                contact={"email": "mi@hru-life.example", "phone": "010-61660012"},
                status="published",
                sort_order=2,
            ),
            Institute(
                name="脑科学与类脑智能研究所",
                slug="brain-science",
                intro="面向脑科学设备、神经调控和智能分析场景开展交叉研究。",
                directions=[
                    {"title": "神经调控技术", "summary": "开展设备评估、应用场景验证和临床合作。"},
                    {"title": "脑数据智能分析", "summary": "探索多模态数据治理和智能辅助分析。"},
                ],
                contact={"email": "brain@hru-life.example", "phone": "010-61660013"},
                status="published",
                sort_order=3,
            ),
            Institute(
                name="智慧药物研究所",
                slug="smart-drug",
                intro="聚焦药物发现、计算筛选和实验评价平台建设。",
                directions=[
                    {"title": "计算筛选", "summary": "提升候选分子发现和验证效率。"},
                    {"title": "评价平台", "summary": "搭建体内外结合的药效评价流程。"},
                ],
                contact={"email": "drug@hru-life.example", "phone": "010-61660014"},
                status="published",
                sort_order=4,
            ),
            Institute(
                name="合成生物学平台研究所",
                slug="synthetic-biology",
                intro="提供菌株构建、表达调控、发酵小试和功能验证服务。",
                directions=[
                    {"title": "工程菌株构建", "summary": "支持底盘细胞改造和表达体系优化。"},
                    {"title": "发酵工艺验证", "summary": "支持小试放大和关键参数评估。"},
                ],
                contact={"email": "synbio@hru-life.example", "phone": "010-61660015"},
                status="published",
                sort_order=5,
            ),
        ]
    )

    now = datetime.now(UTC)
    article_specs = [
        ("怀柔生命科学产业创新研究院门户测试数据上线", "portal-test-data-online", "院内新闻", "门户测试数据库已完成初始化，覆盖首页、新闻、案例、研究所和新增路由页面。", "研究院办公室", True, 0),
        ("研究院组织共性平台开放日活动", "platform-open-day", "院内新闻", "检测评价、实验验证和制剂工艺平台面向企业开放预约咨询。", "平台服务部", False, 1),
        ("首批成果孵化项目进入专家评审", "incubation-review", "院内新闻", "细胞治疗工艺优化和智能康复设备项目进入孵化评审流程。", "成果转化部", False, 2),
        ("生命科学产业创新服务进入平台化发展阶段", "life-science-platform-trend", "行业资讯", "行业服务模式从单点技术支持转向平台化、标准化和数据化协同。", "行业观察", False, 3),
        ("医疗器械创新进入临床需求驱动新周期", "medical-device-demand-cycle", "行业资讯", "临床需求、工程实现和注册路径成为器械转化的关键协同环节。", "产业研究组", False, 4),
        ("关于征集产学研合作项目的通知", "cooperation-project-call", "通知公告", "面向高校院所、医疗机构和创新企业征集联合攻关项目。", "研究院办公室", False, 5),
        ("共性平台预约服务测试开放公告", "platform-reservation-notice", "通知公告", "测试阶段开放平台预约、资料下载和在线咨询入口。", "平台服务部", False, 6),
        ("媒体关注怀柔科学城生命科学转化服务", "media-focus-service", "媒体聚焦", "多家媒体报道怀柔科学城围绕生命科学成果转化形成的服务体系。", "媒体报道", False, 7),
        ("专题报道：从实验室到产业化的怀柔路径", "media-lab-to-industry", "媒体聚焦", "专题报道聚焦研究院在项目筛选、平台验证和资源对接中的作用。", "媒体报道", False, 8),
        ("研究院发布人才服务测试指南", "talent-service-guide-news", "通知公告", "人才服务入口将承接政策咨询、岗位发布和活动报名信息。", "人才服务部", False, 9),
        ("数据统计模块完成首轮口径梳理", "stats-module-caliber", "院内新闻", "后台仪表盘、访问统计和业务统计口径完成测试数据适配。", "数字化办公室", False, 10),
        ("客户端适配测试覆盖三类屏幕", "client-adaptation-test", "院内新闻", "首页、列表页和后台管理页面完成移动端、平板端和桌面端基础观察。", "数字化办公室", False, 11),
    ]
    db.add_all(
        [
            Article(
                title=title,
                slug=slug,
                summary=summary,
                content_html=f"<p>{summary}</p><p>该内容为测试数据库中的演示新闻，用于验证分类筛选、详情跳转、首页推荐和后台维护流程。</p>",
                category_id=category_map[category].id,
                source=source,
                author="内容运营组",
                publish_at=now - timedelta(days=days),
                status="published",
                is_top=is_top,
            )
            for title, slug, category, summary, source, is_top, days in article_specs
        ]
    )

    case_specs = [
        (
            "智慧药物筛选平台合作案例",
            "smart-drug-platform-case",
            "成果转化案例",
            "联合合作方建设药物筛选流程，形成可复用的项目评价服务能力。",
            "示例生物科技企业",
            "产业转化",
            ["平台联合建设", "验证效率提升", "服务能力可复制"],
            1,
        ),
        (
            "微创诊疗器械临床转化案例",
            "minimally-invasive-device-case",
            "平台建设案例",
            "围绕临床需求完成样机评估、专家论证和转化路径梳理。",
            "示例临床机构",
            "临床验证",
            ["临床需求对接", "样机优化", "注册路径咨询"],
            2,
        ),
        (
            "中医药现代评价联合攻关案例",
            "medicine-evaluation-case",
            "产学研合作案例",
            "面向中药活性评价和质量标准形成联合研究方案。",
            "示例高校团队",
            "联合攻关",
            ["活性评价", "标准化研究", "成果转化"],
            3,
        ),
        (
            "合成生物学验证平台服务案例",
            "synthetic-biology-service-case",
            "平台建设案例",
            "通过菌株构建和小试验证支持企业完成工艺路线筛选。",
            "示例合成生物企业",
            "平台服务",
            ["菌株构建", "小试验证", "工艺优化"],
            4,
        ),
        (
            "脑科学设备应用场景验证案例",
            "brain-device-validation-case",
            "成果转化案例",
            "组织临床专家和工程团队完成设备应用场景论证。",
            "示例医疗设备企业",
            "场景验证",
            ["专家论证", "数据评估", "场景验证"],
            5,
        ),
        (
            "人才团队项目落地服务案例",
            "talent-team-service-case",
            "产学研合作案例",
            "围绕创新团队落地提供政策咨询、空间对接和产业资源匹配。",
            "示例创新团队",
            "人才服务",
            ["政策咨询", "空间对接", "产业匹配"],
            6,
        ),
    ]
    db.add_all(
        [
            CaseStudy(
                title=title,
                slug=slug,
                summary=summary,
                category_id=category_map[category].id,
                partner_name=partner_name,
                stage=stage,
                highlights=highlights,
                benefits="测试数据用于展示经济效益、社会效益和平台能力沉淀描述。",
                content_html=f"<p>{summary}</p><p>该案例为测试数据库中的演示内容，用于验证案例列表、分类筛选、详情页和后台录入流程。</p>",
                result_blocks=[
                    {"title": "合作背景", "content": "围绕真实业务场景形成测试展示口径。"},
                    {"title": "阶段成果", "content": "形成可展示的合作路径、服务能力和后续计划。"},
                ],
                publish_at=now - timedelta(days=days),
                status="published",
            )
            for title, slug, category, summary, partner_name, stage, highlights, days in case_specs
        ]
    )

    files = [
        FileRecord(origin_name="平台预约服务指南.pdf", storage_path="uploads/test/platform-guide.pdf", mime_type="application/pdf", size=428000),
        FileRecord(origin_name="产学研合作项目征集表.docx", storage_path="uploads/test/cooperation-form.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=86000),
        FileRecord(origin_name="人才服务政策摘要.pdf", storage_path="uploads/test/talent-policy.pdf", mime_type="application/pdf", size=312000),
    ]
    db.add_all(files)
    db.flush()

    db.add_all(
        [
            DownloadResource(title="平台预约服务指南", slug="平台预约服务指南", summary="说明共性平台服务范围、预约材料和响应流程。", category_id=category_map["服务指南"].id, file_id=files[0].id, sort_order=1),
            DownloadResource(title="产学研合作项目征集表", slug="产学研合作项目征集表", summary="用于合作项目初步信息收集和专家评审。", category_id=category_map["服务指南"].id, file_id=files[1].id, sort_order=2),
            DownloadResource(title="人才服务政策摘要", slug="人才服务政策摘要", summary="汇总人才政策咨询和申报支持的测试材料。", category_id=category_map["政策文件"].id, file_id=files[2].id, sort_order=3),
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
                    "contact_phone": "010-61660000",
                    "contact_email": "contact@hru-life.example",
                    "address": "北京市怀柔科学城创新服务示范区",
                    "icp_no": "京ICP备测试000000号",
                },
            ),
            SiteSetting(
                setting_key="home_stats",
                group_name="homepage",
                setting_value=[
                    {"label": "专业研究所", "value": "5"},
                    {"label": "开放平台", "value": "8"},
                    {"label": "合作项目", "value": "36"},
                    {"label": "服务企业", "value": "58"},
                ],
            ),
            SiteSetting(
                setting_key="quick_links",
                group_name="homepage",
                setting_value=[
                    {"label": "新闻动态", "url": "/news"},
                    {"label": "成功案例", "url": "/cases"},
                    {"label": "共性平台", "url": "/platforms"},
                    {"label": "在线服务", "url": "/service"},
                ],
            ),
            SiteSetting(
                setting_key="seo_defaults",
                group_name="seo",
                setting_value={
                    "seo_title": "北京怀柔科学城生命科学产业创新研究院",
                    "seo_desc": "聚焦生命科学成果转化、共性平台服务、产学研合作和人才服务。",
                    "seo_keywords": "生命科学,成果转化,怀柔科学城,产学研合作,共性平台",
                },
            ),
            SiteSetting(setting_key="footer_links", group_name="footer", setting_value={"links": [{"label": "在线服务", "url": "/service"}, {"label": "人才服务", "url": "/talent"}]}),
            SiteSetting(setting_key="icp_info", group_name="compliance", setting_value={"icp_no": "京ICP备测试000000号", "police_no": "", "analytics_code": ""}),
        ]
    )

    demo_user = User(
        username="demo.user",
        mobile="13900000000",
        email="demo@example.com",
        password_hash=hash_password("DemoPass123!"),
        real_name="演示用户",
        organization="示例合作机构",
        expertise="成果转化",
        status="pending",
        role_id=roles["registered_user"].id,
    )
    active_user = User(
        username="partner.user",
        mobile="13700000000",
        email="partner@example.com",
        password_hash=hash_password("Partner123!"),
        real_name="合作方用户",
        organization="示例生物科技企业",
        expertise="平台服务预约",
        status="active",
        role_id=roles["registered_user"].id,
    )
    db.add_all([demo_user, active_user])
    db.flush()
    db.add(RegistrationApplication(user_id=demo_user.id, review_status="pending"))

    db.add_all(
        [
            ServiceRequest(type="consultation", subject="智慧药物筛选平台预约咨询", contact_name="王女士", contact_mobile="13600000001", contact_email="wang@example.com", organization="示例生物科技企业", content="希望了解平台预约流程和服务周期。"),
            ServiceRequest(type="cooperation", subject="产学研联合攻关意向", contact_name="刘先生", contact_mobile="13600000002", contact_email="liu@example.com", organization="示例高校课题组", content="拟围绕脑科学设备应用场景开展联合验证。"),
            ServiceRequest(type="talent", subject="人才政策咨询", contact_name="赵博士", contact_mobile="13600000003", contact_email="zhao@example.com", organization="创新团队", content="咨询团队落地、政策申报和平台使用支持。"),
        ]
    )

    db.commit()
