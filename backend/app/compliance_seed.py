"""
合规初审模块初始化数据
包含默认检查表模板和示例检查项
"""
from app.core.database import SessionLocal
from app.models.compliance import ComplianceChecklistTemplate, ComplianceCheckItem


def init_compliance_templates(db=None):
    """初始化合规初审检查表模板
    
    Args:
        db: 可选的数据库Session，若为None则内部创建SessionLocal
    """
    own_session = False
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
        own_session = True
    try:
        # 检查是否已有模板
        existing = db.query(ComplianceChecklistTemplate).count()
        if existing > 0:
            print("合规初审模板已存在，跳过初始化")
            return

        # ==================== 模板1：水利工程初步设计合规初审检查表 ====================
        template1 = ComplianceChecklistTemplate(
            template_code="COMP-PS-001",
            template_name="水利工程初步设计合规初审检查表",
            template_type="通用",
            template_stage="初步设计",
            description="适用于各类水利工程初步设计阶段的合规性初审，涵盖资质文件、技术文件、审批流程、法律法规等方面",
            version="1.0",
            is_active=True,
        )
        db.add(template1)
        db.flush()

        # 检查项 - 资质文件类
        items_ps = [
            # 资质文件类
            {
                "category": "资质文件",
                "item_code": "ZZ-001",
                "item_name": "设计单位资质证书",
                "item_description": "检查设计单位是否具备相应等级的水利工程设计资质",
                "check_standard": "设计单位应持有水利行业设计甲级或乙级资质证书，且资质在有效期内",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "reference_docs": [{"name": "水利工程设计资质管理规定", "clause": "第三条"}],
                "sort_order": 1,
            },
            {
                "category": "资质文件",
                "item_code": "ZZ-002",
                "item_name": "项目立项批复文件",
                "item_description": "检查是否具备项目建议书或可行性研究报告的批复文件",
                "check_standard": "应提供发展改革部门或水行政主管部门的立项批复文件",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "critical",
                "reference_docs": [{"name": "水利工程建设程序管理暂行规定", "clause": "第六条"}],
                "sort_order": 2,
            },
            {
                "category": "资质文件",
                "item_code": "ZZ-003",
                "item_name": "勘察设计合同",
                "item_description": "检查是否签订合法有效的勘察设计合同",
                "check_standard": "合同应明确设计范围、内容、深度、工期、费用等条款，双方签字盖章齐全",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 5,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 3,
            },
            {
                "category": "资质文件",
                "item_code": "ZZ-004",
                "item_name": "设计人员资格证书",
                "item_description": "检查主要设计人员是否具备相应执业资格",
                "check_standard": "项目负责人、各专业负责人应具备注册土木工程师（水利水电）等相应执业资格",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 5,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 4,
            },
            # 技术文件类
            {
                "category": "技术文件",
                "item_code": "JS-001",
                "item_name": "设计报告完整性",
                "item_description": "检查初步设计报告章节是否完整、内容是否齐全",
                "check_standard": "应包含综合说明、水文、工程地质、工程任务和规模、工程布置及建筑物、机电及金属结构、施工组织设计、工程占地、水土保持设计、环境影响设计、工程管理设计、设计概算、附件等章节",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "reference_docs": [{"name": "水利水电工程初步设计报告编制规程", "clause": "SL/T 619-2021"}],
                "sort_order": 5,
            },
            {
                "category": "技术文件",
                "item_code": "JS-002",
                "item_name": "水文分析计算",
                "item_description": "检查水文基础资料、分析计算方法和成果合理性",
                "check_standard": "水文资料系列应具有代表性、可靠性、一致性；设计洪水计算方法正确，成果合理",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "high",
                "reference_docs": [{"name": "水利水电工程设计洪水计算规范", "clause": "SL 44-2006"}],
                "sort_order": 6,
            },
            {
                "category": "技术文件",
                "item_code": "JS-003",
                "item_name": "工程地质勘察",
                "item_description": "检查地质勘察工作深度和成果是否满足设计要求",
                "check_standard": "勘察工作量应满足规范要求，地质参数取值合理，主要工程地质问题已查明并提出处理措施",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "high",
                "reference_docs": [{"name": "水利水电工程地质勘察规范", "clause": "GB 50487-2008"}],
                "sort_order": 7,
            },
            {
                "category": "技术文件",
                "item_code": "JS-004",
                "item_name": "工程等别和建筑物级别",
                "item_description": "检查工程等别划分和建筑物级别确定是否正确",
                "check_standard": "应根据《水利水电工程等级划分及洪水标准》SL 252正确划分工程等别和建筑物级别",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "reference_docs": [{"name": "水利水电工程等级划分及洪水标准", "clause": "SL 252-2017"}],
                "sort_order": 8,
            },
            {
                "category": "技术文件",
                "item_code": "JS-005",
                "item_name": "洪水标准确定",
                "item_description": "检查各建筑物洪水标准是否符合规范要求",
                "check_standard": "设计洪水标准、校核洪水标准应符合SL 252及相关专业规范要求",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "sort_order": 9,
            },
            {
                "category": "技术文件",
                "item_code": "JS-006",
                "item_name": "工程布置方案",
                "item_description": "检查工程总体布置方案的合理性和比选论证",
                "check_standard": "应进行多方案技术经济比选，推荐方案理由充分，建筑物布置协调合理",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 10,
            },
            {
                "category": "技术文件",
                "item_code": "JS-007",
                "item_name": "结构安全计算",
                "item_description": "检查主要建筑物结构计算书完整性和正确性",
                "check_standard": "稳定、应力、渗流等计算工况齐全，计算方法正确，参数取值合理，成果满足规范要求",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "sort_order": 11,
            },
            {
                "category": "技术文件",
                "item_code": "JS-008",
                "item_name": "施工组织设计",
                "item_description": "检查施工导流、进度安排、施工方法合理性",
                "check_standard": "施工导流方案合理，施工进度计划可行，主要施工方法得当",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "medium",
                "reference_docs": [{"name": "水利水电工程施工组织设计规范", "clause": "SL 303-2017"}],
                "sort_order": 12,
            },
            {
                "category": "技术文件",
                "item_code": "JS-009",
                "item_name": "设计概算编制",
                "item_description": "检查设计概算编制依据、定额套用和费用计算",
                "check_standard": "概算编制依据正确，定额选用合适，工程量计算准确，费用组成完整",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 13,
            },
            # 审批流程类
            {
                "category": "审批流程",
                "item_code": "LC-001",
                "item_name": "内部校审记录",
                "item_description": "检查设计文件是否经过规定的校审程序",
                "check_standard": "应具备设计、校核、审核、审定各级签字，校审意见已落实",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 14,
            },
            {
                "category": "审批流程",
                "item_code": "LC-002",
                "item_name": "相关部门意见",
                "item_description": "检查是否征求相关部门意见并处理",
                "check_standard": "应征求国土、环保、林业、交通等相关部门意见，对意见采纳情况有说明",
                "check_method": "文件审查",
                "weight": 0.6,
                "score": 5,
                "is_required": False,
                "risk_level": "low",
                "sort_order": 15,
            },
            {
                "category": "审批流程",
                "item_code": "LC-003",
                "item_name": "公众参与和公示",
                "item_description": "检查是否按规定进行公众参与和信息公示",
                "check_standard": "对涉及公众利益的项目应进行公示，公众意见已处理",
                "check_method": "文件审查",
                "weight": 0.5,
                "score": 5,
                "is_required": False,
                "risk_level": "low",
                "sort_order": 16,
            },
            # 法律法规类
            {
                "category": "法律法规",
                "item_code": "FL-001",
                "item_name": "水法符合性",
                "item_description": "检查设计方案是否符合《水法》相关规定",
                "check_standard": "工程建设符合水资源规划、流域综合规划，不影响防洪和第三方合法水事权益",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "reference_docs": [{"name": "中华人民共和国水法", "clause": "第三十八条"}],
                "sort_order": 17,
            },
            {
                "category": "法律法规",
                "item_code": "FL-002",
                "item_name": "防洪法符合性",
                "item_description": "检查是否符合《防洪法》要求，是否进行防洪评价",
                "check_standard": "工程建设符合防洪规划，不降低河道行洪能力，洪评报告已批复",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "critical",
                "reference_docs": [{"name": "中华人民共和国防洪法", "clause": "第二十七条"}],
                "sort_order": 18,
            },
            {
                "category": "法律法规",
                "item_code": "FL-003",
                "item_name": "环境保护要求",
                "item_description": "检查环境影响评价及环保设计",
                "check_standard": "环评报告已批复，环保措施设计到位，生态流量满足要求",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 19,
            },
            {
                "category": "法律法规",
                "item_code": "FL-004",
                "item_name": "水土保持要求",
                "item_description": "检查水土保持方案及设计",
                "check_standard": "水保方案已批复，水土流失防治措施设计到位",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 20,
            },
            {
                "category": "法律法规",
                "item_code": "FL-005",
                "item_name": "建设用地合规性",
                "item_description": "检查工程建设用地是否符合土地利用规划",
                "check_standard": "建设用地预审意见已取得，移民安置规划已审批",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 21,
            },
            # 其他
            {
                "category": "其他",
                "item_code": "QT-001",
                "item_name": "图纸规范签署",
                "item_description": "检查设计图纸签署、图幅、比例是否规范",
                "check_standard": "图纸签署齐全，图面清晰，比例正确，图签完整",
                "check_method": "文件审查",
                "weight": 0.5,
                "score": 5,
                "is_required": True,
                "risk_level": "low",
                "sort_order": 22,
            },
            {
                "category": "其他",
                "item_code": "QT-002",
                "item_name": "设计文件一致性",
                "item_description": "检查设计报告、图纸、概算之间的一致性",
                "check_standard": "报告、图纸、概算中的工程规模、工程量、主要参数应一致",
                "check_method": "文件审查",
                "weight": 0.6,
                "score": 5,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 23,
            },
        ]

        for item_data in items_ps:
            item = ComplianceCheckItem(
                template_id=template1.id,
                **item_data
            )
            db.add(item)

        # ==================== 模板2：堤防工程初步设计专项检查表 ====================
        template2 = ComplianceChecklistTemplate(
            template_code="COMP-DF-001",
            template_name="堤防工程初步设计专项检查表",
            template_type="堤防工程",
            template_stage="初步设计",
            description="适用于堤防工程初步设计阶段的专项合规初审",
            version="1.0",
            is_active=True,
        )
        db.add(template2)
        db.flush()

        items_df = [
            {
                "category": "堤防专项",
                "item_code": "DF-001",
                "item_name": "堤防级别确定",
                "item_description": "检查堤防级别确定是否正确",
                "check_standard": "根据保护对象的重要性、防洪标准正确确定堤防级别",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "reference_docs": [{"name": "堤防工程设计规范", "clause": "GB 50286-2013 第3章"}],
                "sort_order": 1,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-002",
                "item_name": "堤线布置合理性",
                "item_description": "检查堤线布置是否符合规划要求",
                "check_standard": "堤线布置应与河势流向相适应，满足行洪要求，兼顾两岸交通",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 2,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-003",
                "item_name": "堤顶高程确定",
                "item_description": "检查堤顶高程计算是否正确",
                "check_standard": "堤顶高程=设计洪水位+壅高+风浪爬高+安全超高，安全超高值符合规范",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "sort_order": 3,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-004",
                "item_name": "堤身断面设计",
                "item_description": "检查堤身断面尺寸和边坡稳定",
                "check_standard": "堤身断面满足稳定和渗流要求，边坡坡率符合规范",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 4,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-005",
                "item_name": "渗流稳定分析",
                "item_description": "检查渗流计算和渗透稳定分析",
                "check_standard": "渗流计算工况齐全，渗透坡降满足允许坡降要求，渗控措施合理",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "sort_order": 5,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-006",
                "item_name": "抗滑稳定分析",
                "item_description": "检查堤坡抗滑稳定计算",
                "check_standard": "正常、非常工况抗滑稳定安全系数满足规范要求",
                "check_method": "文件审查",
                "weight": 1.2,
                "score": 12,
                "is_required": True,
                "risk_level": "critical",
                "sort_order": 6,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-007",
                "item_name": "堤基处理设计",
                "item_description": "检查软弱堤基处理方案",
                "check_standard": "软基处理措施合理，满足承载力和变形要求",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": False,
                "risk_level": "high",
                "sort_order": 7,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-008",
                "item_name": "护坡护脚设计",
                "item_description": "检查护坡护脚结构设计",
                "check_standard": "护坡护脚形式适应水流条件，抗冲刷能力满足要求",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 8,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-009",
                "item_name": "穿堤建筑物设计",
                "item_description": "检查穿堤建筑物与堤防连接设计",
                "check_standard": "穿堤建筑物与堤防连接可靠，防渗措施到位，接触渗流满足要求",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": False,
                "risk_level": "high",
                "sort_order": 9,
            },
            {
                "category": "堤防专项",
                "item_code": "DF-010",
                "item_name": "防汛道路与管理设施",
                "item_description": "检查防汛道路和管理设施设计",
                "check_standard": "防汛道路满足防汛交通要求，管理设施配置齐全",
                "check_method": "文件审查",
                "weight": 0.6,
                "score": 5,
                "is_required": False,
                "risk_level": "low",
                "sort_order": 10,
            },
        ]

        for item_data in items_df:
            item = ComplianceCheckItem(
                template_id=template2.id,
                **item_data
            )
            db.add(item)

        # ==================== 模板3：可行性研究阶段检查表 ====================
        template3 = ComplianceChecklistTemplate(
            template_code="COMP-KY-001",
            template_name="水利工程可行性研究合规初审检查表",
            template_type="通用",
            template_stage="可行性研究",
            description="适用于水利工程可行性研究阶段的合规初审",
            version="1.0",
            is_active=True,
        )
        db.add(template3)
        db.flush()

        items_ky = [
            {
                "category": "立项程序",
                "item_code": "KY-001",
                "item_name": "流域规划符合性",
                "item_description": "检查项目是否符合流域综合规划和专业规划",
                "check_standard": "项目建设应符合流域综合规划、防洪规划等相关规划，有规划同意书",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "critical",
                "sort_order": 1,
            },
            {
                "category": "立项程序",
                "item_code": "KY-002",
                "item_name": "项目建议书批复",
                "item_description": "检查是否有项目建议书批复文件",
                "check_standard": "需提供项目建议书批复文件作为可研编制依据",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 2,
            },
            {
                "category": "技术方案",
                "item_code": "KY-003",
                "item_name": "水文分析成果合理性",
                "item_description": "检查水文分析计算成果",
                "check_standard": "水文基础资料可靠，计算方法正确，成果基本合理",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 3,
            },
            {
                "category": "技术方案",
                "item_code": "KY-004",
                "item_name": "工程地质勘察结论",
                "item_description": "检查地质勘察主要结论",
                "check_standard": "区域地质和工程地质条件已基本查明，主要地质问题已识别",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 4,
            },
            {
                "category": "技术方案",
                "item_code": "KY-005",
                "item_name": "工程规模论证",
                "item_description": "检查工程规模论证充分性",
                "check_standard": "工程规模论证充分，供需分析或防洪能力分析合理",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 5,
            },
            {
                "category": "技术方案",
                "item_code": "KY-006",
                "item_name": "工程方案比选",
                "item_description": "检查是否进行多方案比选",
                "check_standard": "应对工程选址、总体布置、主要建筑物型式进行多方案技术经济比选",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 6,
            },
            {
                "category": "投资估算",
                "item_code": "KY-007",
                "item_name": "投资估算编制",
                "item_description": "检查投资估算编制合理性",
                "check_standard": "投资估算编制依据正确，工程量估算基本合理，费用组成完整",
                "check_method": "文件审查",
                "weight": 1.0,
                "score": 10,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 7,
            },
            {
                "category": "经济评价",
                "item_code": "KY-008",
                "item_name": "经济评价",
                "item_description": "检查国民经济评价和财务分析",
                "check_standard": "国民经济评价指标合理，财务分析可行，敏感性分析完整",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 8,
            },
            {
                "category": "前期要件",
                "item_code": "KY-009",
                "item_name": "相关专题报告",
                "item_description": "检查环评、水保、洪评、移民等专题",
                "check_standard": "环境影响评价、水土保持、防洪影响评价、移民安置规划等专题已开展或有安排",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "high",
                "sort_order": 9,
            },
            {
                "category": "前期要件",
                "item_code": "KY-010",
                "item_name": "建设资金筹措",
                "item_description": "检查资金筹措方案",
                "check_standard": "资金来源明确，筹措方案可行",
                "check_method": "文件审查",
                "weight": 0.8,
                "score": 8,
                "is_required": True,
                "risk_level": "medium",
                "sort_order": 10,
            },
        ]

        for item_data in items_ky:
            item = ComplianceCheckItem(
                template_id=template3.id,
                **item_data
            )
            db.add(item)

        db.commit()
        print("合规初审检查表模板初始化完成")
        print(f"- 已创建模板: {template1.template_name} ({len(items_ps)}项)")
        print(f"- 已创建模板: {template2.template_name} ({len(items_df)}项)")
        print(f"- 已创建模板: {template3.template_name} ({len(items_ky)}项)")

    except Exception as e:
        db.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    init_compliance_templates()
