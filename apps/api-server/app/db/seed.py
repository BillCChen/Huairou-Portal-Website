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
        ("院内动态", "院内动态", "article", 1),
        ("活动与沙龙", "活动与沙龙", "article", 2),
        ("科普教育", "科普教育", "article", 3),
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
        Tag(name="院内动态", slug="院内动态", type="新闻", color="#0f5b78"),
        Tag(name="活动与沙龙", slug="活动与沙龙", type="新闻", color="#0f766e"),
        Tag(name="科普教育", slug="科普教育", type="新闻", color="#b45309"),
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
                subtitle="展示研究合作成果案例，连接成果转化平台促进交流对接。",
                button_text="查看院内动态",
                button_url="/news?category_slug=院内动态",
                tag="院内动态",
                sort_order=1,
                is_enabled=True,
            ),
            Banner(
                title="重大设施平台开放共享",
                subtitle="围绕检测评价、实验验证和产业转化举办系列开放共享沙龙。",
                button_text="查看活动与沙龙",
                button_url="/news?category_slug=活动与沙龙",
                tag="活动与沙龙",
                sort_order=2,
                is_enabled=True,
            ),
            Banner(
                title="科学教育与科普活动",
                subtitle="走进怀柔科学城，开展面向青少年的科学教育与科普实践。",
                button_text="查看科普教育",
                button_url="/news?category_slug=科普教育",
                tag="科普教育",
                sort_order=3,
                is_enabled=True,
            ),
            Banner(
                title="媒体关注怀柔生命科学创新",
                subtitle="集中呈现媒体报道、专题采访和产业观察内容。",
                button_text="查看媒体聚焦",
                button_url="/news?category_slug=媒体聚焦",
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
            "<p>北京怀柔科学城生命科学产业创新研究院由怀柔科学城管委会联合北京大学、中国科学院大学、中国科学院自动化所等共同发起设立，深耕生命科学核心产业领域，采用“633”科技成果转化模式。</p><p>研究院依托怀柔科学城生命科学领域 12 个科学设施平台、1 家新型研发机构（北京干细胞与再生医学研究院）、2 所大学（中国科学院大学和北京大学怀密医学中心），统筹产业研究、成果转化、人才培养与基金体系建设，实行理事会领导下的院长负责制，以市场化导向引领生命科学产业创新发展。</p>",
            [
                {"type": "定位", "title": "功能定位", "content": "搭建“实验室到市场”的桥梁，聚焦生命科学关键产业，构建“科学大装置＋研究院＋孵化器＋产业园＋领军企业＋医疗机构＋区域协同生产”的协同创新模式，提供成果发现、筛选、评估、优化、撮合、要素匹配及市场推广的全流程转化服务。"},
                {"type": "机制", "title": "协同机制", "content": "采用“633 模式”和“院企二元机制”。633 模式聚焦生物医学影像、智慧药物、现代化中药、肿瘤诊疗、脑科学与类脑智能、干细胞与再生医学六大产业领域，依托科技设施平台、产业创新研究院、创新联合体三类创新主体，布局孵化器、产业园区、区域协同生产基地三类产业空间；院企二元机制下研究院负责技术路线与孵化管理，平台公司负责投资合作与团队激励。"},
                {"type": "使命", "title": "使命愿景", "content": "培育生命科学新质生产力，立足设施平台、科研团队、科技成果等要素聚集优势，加速科技成果转化与产业化，服务“面向人民生命健康”的国家科技战略需求。"},
                {"type": "战略", "title": "发展战略", "content": "以“科学问题牵引→设施平台支撑→成果转化落地→产业集群培育”为发展模式，构建“123 生命科学产业体系”：1 个主导产业（生物医学影像），2 个支撑产业（智慧药物、现代化中药），3 个重点培育产业（肿瘤诊疗、干细胞与再生医学、脑科学与类脑智能）。"},
                {"type": "治理", "title": "治理结构", "content": "实行理事会领导下的院长负责制，设立全球战略咨询委员会，下设技术服务平台、综合服务办公室、平台公司。"},
                {"type": "联系", "title": "联系方式", "content": "地址：北京市怀柔区永乐北二街 9 号院 5 号楼 3 层 301 室－1；邮箱：cyy@lsiii.com。"},
            ],
        ),
        (
            "contact",
            "联系我们",
            "<p>地址：北京市怀柔区永乐北二街 9 号院 5 号楼 3 层 301 室－1。</p><p>邮箱：cyy@lsiii.com。</p>",
            [],
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
            "platforms",
            "共性平台",
            "<p>研究院依托怀柔科学城生命科学领域的科学设施平台，面向外部开放实验验证、检测评价与技术服务能力。以下为已接入资源库的代表性科学设施平台。</p>",
            [
                {"type": "平台", "title": "高能同步辐射光源", "content": "高能量、高亮度同步辐射光源，支撑结构解析与成像研究。"},
                {"type": "平台", "title": "先进光源技术研发与测试平台", "content": "面向先进光源关键技术的研发与测试。"},
                {"type": "平台", "title": "多模态跨尺度生物医学成像设施", "content": "支撑多模态、跨尺度生物医学成像研究。"},
                {"type": "平台", "title": "新发突发传染病疫苗抗体智能分析测试平台", "content": "面向疫苗与抗体的智能分析与测试。"},
                {"type": "平台", "title": "北京激光加速创新中心", "content": "开展激光加速前沿技术研究与应用。"},
                {"type": "平台", "title": "脑认知机理与脑机融合交叉研究平台", "content": "聚焦脑认知机理与脑机融合交叉研究。"},
                {"type": "平台", "title": "脑认知功能图谱与类脑智能交叉研究平台", "content": "支撑脑认知功能图谱与类脑智能研究。"},
                {"type": "平台", "title": "分子影像与医学诊疗探针创新平台", "content": "面向分子影像与医学诊疗探针的创新研发。"},
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

    leader_specs = [
        ("张礼和", "理事长 · 北京大学药学院教授", "核酸化学及抗肿瘤抗病毒药物研究"),
        ("陈全生", "全球战略咨询委员会专家委员", "产业经济与政策研究"),
        ("乐玉成", "全球战略咨询委员会专家委员", "国际战略、中外经贸与科技合作"),
        ("刘国恩", "全球战略咨询委员会专家委员 · 北京大学全球健康发展研究院院长", "健康产业、医药政策与医保研究"),
        ("张海滨", "全球战略咨询委员会专家委员 · 北京大学国际关系学院副院长", "全球环境治理与国际关系"),
        ("孙育杰", "院长 · 北京大学未来技术学院副院长", "分子生物学、基因调控机制"),
        ("姜志奇", "执行院长", "科技成果转化"),
        ("黄韶辉", "副院长", "科学仪器创新研究"),
        ("陈庚", "副院长", "金融管理"),
        ("宋星", "副院长", "工程管理"),
        ("刘振明", "副院长 · 北京大学药学院研究员", "药物设计与合成、计算化学与分子模拟、药物信息学、人工智能辅助药物研发"),
        ("刘晋伟", "副院长", "高校管理与地方教育规划"),
        ("侯学谦", "办公室主任", "工商管理"),
        ("韩华", "脑科学与类脑智能研究中心所长 · 研究员", "模式识别与智能系统"),
        ("郎明林", "糖基科学研究所所长 · 中国科学院大学教授", "生命科学"),
        ("李彬", "中医药现代化创新研究所所长 · 北京中医医院副院长", "针灸治疗代谢病与痛症"),
        ("张建国", "微创医学转化研究所所长 · 航空总医院消化内科主任", "消化内镜诊疗"),
        ("张俊祥", "产研院研究员", "大健康产业规划研究"),
        ("张奇龙", "产研院研究员", "金融投资"),
        ("李之韫", "产研院研究员", "产业经济与政策研究"),
        ("张衡", "中国科学院高能物理研究所副研究员", "化学生物学"),
        ("胡正义", "中国科学院大学中丹学院副院长", "土壤环境化学"),
        ("常振战", "北京大学医学部生物物理学系副教授", "生物物理学和药学、经络、武术"),
        ("陈曦", "中国科学院自动化研究所研究员", "生物医学图像处理、体电子显微学"),
        ("梁淼", "中国科学院高能物理研究所工程师", "无机化学、串行晶体学"),
        ("曾克武", "北京大学药学院研究员", "天然药物化学"),
    ]
    db.add_all(
        [
            Leader(name=name, title=title, intro=f"擅长领域：{expertise}", sort_order=index)
            for index, (name, title, expertise) in enumerate(leader_specs, start=1)
        ]
    )

    institute_contact = {"phone": "", "email": ""}
    db.add_all(
        [
            Institute(
                name="脑科学与类脑智能研究中心",
                slug="brain-science-intelligence",
                intro="聚焦脑科学前沿与类脑智能核心技术，围绕神经环路解析、脑疾病早期诊断与精准治疗、类脑芯片与智能系统等方向开展系统性研究，推动脑科学基础研究成果向智能终端、医疗机器人等领域的转化应用。",
                directions=[
                    {"title": "神经环路解析与脑疾病诊疗", "summary": "开展神经环路解析、脑疾病早期诊断与精准治疗研究。"},
                    {"title": "类脑芯片与智能系统", "summary": "推动类脑芯片、智能终端与医疗机器人转化应用。"},
                ],
                contact=institute_contact,
                status="published",
                sort_order=1,
            ),
            Institute(
                name="微创医学转化研究所",
                slug="minimally-invasive-medicine",
                intro="由航空总医院消化内科主任张建国领衔，依托怀柔医院建设全国首家NOEES示范、培训及诊疗器械创新中心，聚焦原创超级微创技术转化，开展器械研发、临床验证与规范制定，打造具有全球影响力的“中国方案”。",
                directions=[
                    {"title": "原创超级微创技术转化", "summary": "聚焦 NOEES 等原创超级微创技术的器械研发与临床验证。"},
                    {"title": "诊疗器械创新与规范制定", "summary": "建设诊疗器械创新中心，推动技术规范与标准制定。"},
                ],
                contact=institute_contact,
                status="published",
                sort_order=2,
            ),
            Institute(
                name="AI 智慧药物研究所",
                slug="ai-smart-drug",
                intro="深度衔接中国科学院高能物理研究所、怀密医学中心、望石智慧技术资源，聚焦创新药物研发，支持 FBDD 源头创新药进入临床，填补国内相关领域空白，构建覆盖 AI 药物设计、合成、活性检测、成药性评价的一体化科研与转化平台。",
                directions=[
                    {"title": "FBDD 源头创新药研发", "summary": "支持基于片段的源头创新药研发并推进临床转化。"},
                    {"title": "AI 药物一体化平台", "summary": "构建 AI 药物设计、合成、活性检测与成药性评价一体化平台。"},
                ],
                contact=institute_contact,
                status="published",
                sort_order=3,
            ),
            Institute(
                name="糖基科学研究所",
                slug="glycoscience",
                intro="通过华医科协的国际医疗力量，依托中国科学院、国科大，整合各类国际糖科学研究及应用资源，加速推动糖科学的科技研发、人才培养、成果转化和产业培育，打造集糖科学基础研究、临床应用衔接、产业孵化支撑于一体的专业化研究机构。",
                directions=[
                    {"title": "糖科学研发与人才培养", "summary": "整合国际糖科学资源，推动科技研发与人才培养。"},
                    {"title": "临床应用与产业孵化", "summary": "衔接糖科学临床应用并提供产业孵化支撑。"},
                ],
                contact=institute_contact,
                status="published",
                sort_order=4,
            ),
            Institute(
                name="医学影像设备研究所",
                slug="medical-imaging-equipment",
                intro="聚焦多模态跨尺度生物医学成像设施等平台产出的先进影像设备关键技术与系统，推动成像装备在生命科学、药物研发及疾病机制研究中的创新应用，培养医学影像、分子影像及核医学等领域复合型科研人才。",
                directions=[
                    {"title": "先进影像设备关键技术", "summary": "研发多模态跨尺度成像设备关键技术与系统。"},
                    {"title": "成像装备创新应用", "summary": "推动成像装备在生命科学与药物研发中的应用。"},
                ],
                contact=institute_contact,
                status="published",
                sort_order=5,
            ),
            Institute(
                name="中医药现代化创新研究所",
                slug="tcm-modernization",
                intro="由产研院与首都医科大学附属北京中医医院共建，聚焦中医机理阐释、经典制剂产业升级、复合型人才培育与创新平台搭建四大方向，推动中医药现代化创新与成果转化。",
                directions=[
                    {"title": "中医机理阐释与制剂升级", "summary": "开展中医机理阐释与经典制剂产业升级。"},
                    {"title": "人才培育与创新平台", "summary": "培育复合型人才并搭建中医药创新平台。"},
                ],
                contact=institute_contact,
                status="published",
                sort_order=6,
            ),
        ]
    )

    now = datetime.now(UTC)
    article_specs = [
        ("北京怀柔科学城生命科学产业创新研究院揭牌，打造生命科学产业新高地", "institute-unveiling", "院内动态", "研究院在第四届雁栖人才论坛揭牌运行，一期设立医学影像设备、中医药现代化创新转化等六个专业研究所。", "怀柔科学城", True, "2024-11-23"),
        ("分子影像与医学诊疗探针创新平台土建工程竣工验收", "imaging-probe-platform-acceptance", "院内动态", "平台土建工程通过竣工验收，转入设备安装与平台建设阶段。", "北京怀柔科学城产研院", False, "2026-05-30"),
        ("十三个重大项目集中签约，生命健康领域加速成果转化", "platform-empowering-signing", "院内动态", "怀柔科学城重大项目集中签约，生命健康领域依托科研平台集聚优势推进国产创新药物研发等合作。", "怀柔科学城", False, "2025-09-26"),
        ("“让大脑描绘未来”脑科学主题产业沙龙成功举办", "brain-science-salon", "活动与沙龙", "生命科学重大设施平台开放共享系列沙龙第二期在城市客厅举办，百余位科研、企业与投资机构代表参加。", "怀柔科学城", False, "2024-11-08"),
        ("生命科学重大设施平台开放共享系列沙龙首期成功举办", "platform-sharing-salon-first", "活动与沙龙", "首期沙龙为科研院所成果发布、投资机构项目遴选和企业路演搭建联动桥梁。", "怀柔科学城", False, "2024-10-22"),
        ("中医药科产融合创新沙龙暨走进大科学装置活动成功举办", "tcm-innovation-salon", "活动与沙龙", "围绕中医药科产融合，青年委员会走进怀柔科学城大科学装置开展交流对接。", "北京怀柔科学城产研院", False, "2026-05-16"),
        ("技术经理人培训体系启动，年内举办两期培训班", "tech-manager-training", "活动与沙龙", "面向京津冀创新主体的技术经理人培训累计吸引六百余人次参与。", "北京怀柔科学城产研院", False, "2024-12-05"),
        ("探秘数学世界，点亮科学梦想——怀柔科学城科学教育活动圆满举办", "math-science-education", "科普教育", "面向青少年的科学教育活动走进怀柔科学城，以数学探索点亮科学梦想。", "北京怀柔科学城产研院", False, "2026-06-05"),
        ("校地协同促融合 科教共研结硕果——首都师范大学附属学校走进产研院", "school-coordination", "科普教育", "首都师范大学附属怀柔科学城学校与产研院开展校地科教协同，共建科学教育实践。", "北京怀柔科学城产研院", False, "2026-05-27"),
        ("媒体聚焦：研究院揭牌打造我国生命科学产业新高地", "media-unveiling-coverage", "媒体聚焦", "中国日报、光明网等媒体报道研究院揭牌，聚焦怀柔生命科学产业创新生态建设。", "中国日报、光明网", False, "2024-11-28"),
        ("《北京日报》整版报道：怀柔建设国际一流战略科技融合发展示范区", "beijing-daily-report", "媒体聚焦", "《北京日报》整版报道怀柔以科学设施平台赋能产业、推动战略科技融合发展。", "北京日报", False, "2026-01-07"),
    ]
    db.add_all(
        [
            Article(
                title=title,
                slug=slug,
                summary=summary,
                content_html=f"<p>{summary}</p>",
                category_id=category_map[category].id,
                source=source,
                publish_at=datetime.fromisoformat(published).replace(tzinfo=UTC),
                status="published",
                is_top=is_top,
            )
            for title, slug, category, summary, source, is_top, published in article_specs
        ]
    )

    case_specs = [
        (
            "生物切片阵列大面积离子减薄仪",
            "ion-thinning-instrument",
            "成果转化案例",
            "面向脑联接图谱的神经组织样品制备，将大口径等离子束应用于连续切片阵列逐层减薄，切片厚度可降至 10nm。",
            "聚焦微观尺度脑联接图谱绘制的神经组织样品制备需求，创新性地将大口径等离子束应用于生物组织连续切片阵列的逐层减薄，可将切片厚度降至 10nm，为我国脑科学和类脑研究提供突触水平神经结构重建必需的关键核心仪器和解决方案。",
            "中国科学院自动化研究所",
            "中国科学院自动化研究所",
            "关键仪器研制",
            ["切片厚度降至 10nm", "突触尺度神经网络重构", "高空间分辨率、高稳定性"],
            2,
        ),
        (
            "共振角检测式 SPR 成像系统",
            "spr-imaging-system",
            "平台建设案例",
            "融合 SPR 高准确度与 SPR 成像高通量，开发下一代生物分子互作分析平台，推动高端 SPR 设备国产化替代。",
            "融合表面等离子共振（SPR）高准确度与 SPR 成像高通量优势，开发下一代生物分子互作分析平台，将先导化合物发现周期从 1-3 年压缩至 6-12 个月，样本消耗降至 pg 级别，实现高端 SPR 设备国产化替代。检测通量 ≥9000 样/轮，空间分辨率 <100nm。",
            "北京大学、北京怀柔科学城生命科学产业创新研究院",
            "王倩（北京大学副主任技师）",
            "国产化替代",
            ["近万级检测通量", "纳米级空间分辨率", "国产化替代打破垄断"],
            5,
        ),
        (
            "小动物五模态分子成像设备",
            "five-modal-imaging-device",
            "成果转化案例",
            "全球首台五模态小动物同机融合成像系统，整合 MRI、PET、SPECT、CT、FMI 五种模态。",
            "全球首台五模态小动物同机融合成像系统，整合 MRI、PET、SPECT、CT 和 FMI 五种模态，实现各技术性能最优化及多模态信息叠加关联，为肿瘤研究、药物研发等领域提供一体化成像手段，推动原创性成果产出。",
            "北京大学",
            "任秋实（北京大学教授、首席科学家）",
            "成果转化",
            ["全球首台五模态融合", "多模态信息叠加关联", "一体化成像手段"],
            8,
        ),
        (
            "糖基测序仪",
            "glycan-sequencer",
            "成果转化案例",
            "优化糖基测序仪性能实现国产替代，通过高灵敏度糖链检测服务科研、临床诊断和健康管理。",
            "糖基化异常与癌症、神经退行性疾病等密切相关。项目优化糖基测序仪性能，实现国产替代，突破临床转化瓶颈，通过高灵敏度的糖链检测服务于科研探索、临床诊断和健康管理三大场景，实现精准、高效、低成本、自动化。",
            "中国科学院大学",
            "中国科学院大学团队",
            "国产替代",
            ["高灵敏度糖链检测", "三大应用场景", "精准高效低成本"],
            11,
        ),
        (
            "智能高精准显微眼科手术机器人",
            "ophthalmic-surgery-robot",
            "成果转化案例",
            "解决显微外科微尺度操作精度与操作力感知难题，已在北京同仁、朝阳医院开展临床试用。",
            "针对显微外科手术中微尺度操作精度超人手生理极限、操作力难以感知、视野受限等临床痛点研制。产品已完成样机迭代验证、活体兔和猪实验及临床前实验，并在北京同仁医院、北京朝阳医院开展临床试用，技术及产业化条件成熟。",
            "中国科学院自动化研究所",
            "边桂彬研究员、何文浩研究员",
            "临床试用",
            ["突破人手操作精度极限", "微力感知", "多中心临床试用"],
            14,
        ),
        (
            "中西医融合 AI 大模型及全生命周期健康管理系统",
            "tcm-western-ai-health",
            "产学研合作案例",
            "融合中医整体观与西医循证医学，构建集“防、监、治、养”于一体的全链条健康管理。",
            "贯彻中西医并重方针，推动中医整体观与西医循证医学深度融合，以人工智能构建个体健康状态全维感知与精准干预体系，打造集“防、监、治、养”于一体的全链条健康管理服务，聚焦高血压、糖尿病等慢性病实施动态监测与个性化方案优化。",
            "北京中医医院、北京大学、怀柔科学城生命科学产业研究院",
            "中医、西医、AI 算法、数据科学及健康管理专家",
            "系统研发",
            ["中西医深度融合", "AI 全维健康感知", "慢病动态监测"],
            17,
        ),
        (
            "中医药智能茶饮机",
            "tcm-smart-tea-machine",
            "成果转化案例",
            "融合物联网、中医 AI 面诊与药食同源茶饮工艺，基于体质辨识提供个性化茶饮推荐。",
            "研究院联合春风药业、一清研究院研制智慧药膳自助茶饮机及配套茶饮，融合物联网控制、中医 AI 面诊与药食同源茶饮工艺，实现基于面部特征的体质辨识个性化茶饮推荐，布局中医院、写字楼、地铁火车站等消费场景。",
            "北京怀柔科学城生命科学产业创新研究院、春风药业、一清研究院",
            "研究院联合企业团队",
            "市场推广",
            ["中医 AI 面诊体质辨识", "药食同源茶饮", "多场景布局"],
            20,
        ),
        (
            "居家麦粒灸专用仪",
            "home-moxibustion-device",
            "成果转化案例",
            "全球首创居家麦粒灸专用仪，解决传统麦粒灸操作繁琐、烫伤风险高等痛点，注册 2 类医疗器械。",
            "传统麦粒灸依赖人工完成“捻、按、取灰”等操作，流程繁琐且烫伤风险高、烟雾大。产研院与北京中医医院合作开发全球首创居家麦粒灸专用仪，注册 2 类医疗器械，解决居家及医疗机构使用难题。",
            "北京怀柔科学城生命科学产业创新研究院、北京中医医院",
            "产研院与北京中医医院联合团队",
            "器械注册",
            ["全球首创麦粒灸专用仪", "2 类医疗器械注册", "解决居家使用难题"],
            23,
        ),
        (
            "药食同源产品",
            "medicinal-food-products",
            "产学研合作案例",
            "以中医院经典方剂为基础开发药食同源功能饮食，并揭示新型植物提取物改善阿尔茨海默病机理。",
            "与北京中医医院联合开发山花消挫饮、享瘦饮、参戟强筋丸、杞栀悦心口服液、枳桔解酒方等药食同源产品，以 5 个经典方剂为基础开发功能饮食；首次揭示源自传统药食两用作物的新型提取物（NPE）通过调节“脂肪体（肝）-脑轴”铁代谢改善 AD 病理，显著提升模型动物的寿命、运动能力及学习记忆能力。",
            "北京怀柔科学城生命科学产业创新研究院、北京中医医院",
            "产研院与北京中医医院联合团队",
            "产品开发",
            ["经典方剂功能饮食", "NPE 改善 AD 病理", "多人群细分产品"],
            26,
        ),
    ]
    db.add_all(
        [
            CaseStudy(
                title=title,
                slug=slug,
                summary=summary,
                category_id=category_map[category].id,
                partner_name=source,
                stage=stage,
                highlights=highlights,
                content_html=f"<p>{description}</p>",
                result_blocks=[
                    {"title": "项目来源", "content": source},
                    {"title": "负责团队", "content": team},
                ],
                publish_at=now - timedelta(days=days),
                status="published",
            )
            for title, slug, category, summary, description, source, team, stage, highlights, days in case_specs
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
                    "site_subtitle": "深耕生命科学核心产业，采用“633”科技成果转化模式，搭建实验室到市场的桥梁。",
                    "mission": "培育生命科学新质生产力，加速科技成果转化与产业化。",
                    "vision": "打造生命科学领域的产业创新生态系统，推动原始创新突破与产业集群培育。",
                    "strategy": "构建“123 生命科学产业体系”，聚焦生物医学影像主导产业及智慧药物、现代化中药等支撑培育产业。",
                    "governance": "理事会领导下的院长负责制，设全球战略咨询委员会，下设技术服务平台、综合服务办公室与平台公司。",
                    "contact_phone": "",
                    "contact_email": "cyy@lsiii.com",
                    "address": "北京市怀柔区永乐北二街 9 号院 5 号楼 3 层 301 室－1",
                    "icp_no": "京ICP备测试000000号",
                },
            ),
            SiteSetting(
                setting_key="home_stats",
                group_name="homepage",
                setting_value=[
                    {"label": "科学设施平台", "value": "12"},
                    {"label": "专业研究所", "value": "6"},
                    {"label": "重点转化项目", "value": "9"},
                    {"label": "产业领域", "value": "6"},
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
            SiteSetting(setting_key="footer_links", group_name="footer", setting_value={"links": [{"label": "在线服务", "url": "/service"}]}),
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
