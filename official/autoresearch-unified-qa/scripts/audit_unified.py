#!/usr/bin/env python3
"""Read-only complete AutoResearch review, followed by scoped legacy waivers.

No submitted Python, shell, model, Docker image, Harbor or network endpoint is run.
Review worksheets are internal reviewer output, never new author requirements.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import audit_task
import audit_format_repair as fmt
import audit_standard_with_waivers as migration
import implementation_review as core
import content_gates

VERSION = '0.4.4-compat-dialogue.2'
PROVIDERS = ('unknown', 'innerfield-maso-v1', 'mido-2026-11-03', 'generic-harbor')
MODES = ('standard', 'legacy-waiver')
INTAKE_COHORTS = ('unspecified', 'legacy_831', 'new_1104')
ROLLOUT_POLICIES = ('source_only', 'historical_1h', 'scored_required')
TARGET_LEVELS = ('L0', 'L1', 'L2')
SUCCESS = {'pass', 'not_applicable', 'pass_with_waivers', 'waived'}
CORE_IDS = list(content_gates.IDS) + list(core.IDS) + [f'H{i:02}' for i in range(1,6)] + ['T01','T02']


def dump(path, value):
    fmt.atomic_write(Path(path), json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def load_review(path):
    if path is None:
        return None
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('内部底稿超过64MiB，请拆分原始材料引用；这不是专家题包大小限制。')
    def reject(value):
        raise ValueError('non-finite JSON constant: ' + value)
    result = json.loads(path.read_text(encoding='utf-8'), parse_constant=reject)
    if not isinstance(result, dict):
        raise ValueError('统一审核底稿必须是JSON对象。')
    return result


def context(worksheet, mode=None, provider=None, stage=None, *, intake_cohort=None, rollout_policy=None, target_level=None):
    supplied = (worksheet or {}).get('context') or {}
    if not isinstance(supplied, dict):
        raise ValueError('context必须是对象。')
    result = dict(supplied)
    for key, value, default in [('mode',mode,'legacy-waiver'), ('provider',provider,'unknown'), ('package_stage',stage,'source')]:
        if value is not None and key in result and result[key] != value:
            raise ValueError('CLI与审核底稿的context.' + key + '不一致。')
        result[key] = value if value is not None else result.get(key, default)
    if result['mode'] not in MODES or result['provider'] not in PROVIDERS or result['package_stage'] not in {'source','runtime'}:
        raise ValueError('不支持的mode、provider或package_stage。')
    for key,value,allowed in [('intake_cohort',intake_cohort,INTAKE_COHORTS),
                              ('rollout_policy',rollout_policy,ROLLOUT_POLICIES),('target_level',target_level,TARGET_LEVELS)]:
        if value is not None:
            if key in result and result[key] != value:
                raise ValueError('CLI与审核底稿的context.'+key+'不一致。')
            result[key]=value
        if key in result and result[key] not in allowed:
            raise ValueError('不支持的context.'+key+'。')
    if result.get('rollout_policy')=='historical_1h' and result.get('intake_cohort')!='legacy_831':
        raise ValueError('historical_1h只说明已授权存量831批次的旧准入，不能推广给新批次。')
    if result.get('intake_cohort')=='new_1104' and result['mode']=='legacy-waiver':
        raise ValueError('new_1104须使用standard模式，不能继承存量豁免。')
    return result


def prepare_standard(worksheet, ctx):
    sr = copy.deepcopy((worksheet or {}).get('standard'))
    if sr is None:
        return None
    if not isinstance(sr, dict):
        raise ValueError('standard必须是原完整审阅底稿对象。')
    hr = sr.setdefault('harbor', {})
    if not isinstance(hr, dict):
        raise ValueError('standard.harbor必须是对象。')
    existing = hr.get('deployment_profile')
    if existing and existing != ctx['provider']:
        raise ValueError('context.provider与standard.harbor.deployment_profile不一致。')
    hr['deployment_profile'] = ctx['provider']
    hr['delivery_stage'] = ctx['package_stage']
    return sr


def missing_row(key, summary='该项尚未完成内容审阅，不能由文件存在或其他项通过代替。'):
    return {'id':key, 'status':'manual', 'summary':summary, 'evidence':[], 'review_complete':False}


def standard_rows(native, components, review=None):
    rows = []
    rows += components.get('content_gates', native.get('content_gates', {})).get('checks', [])
    rows += native.get('checks', [])
    rows += components.get('harbor', native.get('harbor', {})).get('checks', [])
    integrity = components.get('trajectory', native.get('trajectory_review') or {})
    overview = components.get('overview', native.get('overview') or {})
    for index, item in enumerate(overview.get('trajectories', [])[:2], 1):
        record = next((r for r in integrity.get('trajectories', []) if r.get('name') == item.get('name')), {})
        findings = record.get('findings', [])
        bad = record.get('content_status')=='fail' or any(f.get('certainty') == 'confirmed' and f.get('score_effect') == 'invalid' for f in findings)
        read = record.get('content_status')=='pass' and not record.get('unresolved_candidates') and not integrity.get('unreviewed_sources')
        rows.append({'id':f'T{index:02}', 'title':'实际轨迹内容与会话审阅', 'status':'fail' if bad else 'pass' if read and item.get('status') not in {'missing','unreadable'} else 'manual',
            'summary': record.get('summary') or ('已有轨迹行为、方法和分数来源已核对。' if read else '需实际审阅已交轨迹及相关会话；不能仅看摘要。'),
            'evidence': list(dict.fromkeys([p for p in [item.get('source_path')] if p] + record.get('evidence', []))), 'details':record})
    indexed = {}
    for row in rows:
        key = row.get('id')
        if key in CORE_IDS:
            if key in indexed:
                raise ValueError('基础检查ID重复：' + key)
            indexed[key] = copy.deepcopy(row)
    result=[indexed.get(key, missing_row(key)) for key in CORE_IDS]
    annotate_deployment_causes(result,components.get('harbor',native.get('harbor',{})),review)
    annotate_resource_causes(result,components.get('resources',native.get('resource_review') or {}),components.get('harbor',native.get('harbor',{})),review)
    return result


def annotate_deployment_causes(rows, harbor, review=None):
    failures=[r for r in harbor.get('deployment_contract',{}).get('findings',[]) if r.get('status')=='fail']
    if not failures: return
    row=next((r for r in rows if r['id']=='H02'),None)
    if row is None: return
    row['automatic_findings']=[{**r,'summary':r.get('message',r.get('summary',''))} for r in failures]
    declared=next((r for r in ((review or {}).get('harbor') or {}).get('checks',[]) if r.get('id')=='H02'),{})
    row['review_status']=declared.get('status')


def annotate_resource_causes(rows, resources, harbor, review=None):
    row=next((r for r in rows if r['id']=='QA15'),None)
    if row is None or not resources.get('problems'): return
    deployment=harbor.get('deployment_contract',{}).get('findings',[])
    causes=[]
    for message in resources['problems']:
        cause=next((r for r in deployment if r.get('message')==message and r.get('status')=='fail'),None)
        causes.append({**(cause or {}),'summary':message,'evidence':resources.get('evidence',[])})
    row['automatic_findings']=causes
    row['review_status']=((review or {}).get('resource_review') or {}).get('status')


def run_core(root, worksheet, ctx, out):
    sr = prepare_standard(worksheet, ctx)
    if ctx['mode'] == 'legacy-waiver':
        lr = copy.deepcopy((worksheet or {}).get('legacy'))
        if lr is not None:
            if not isinstance(lr, dict):
                raise ValueError('legacy必须是逐原因豁免底稿对象。')
            lr['deployment_profile'] = ctx['provider']
            lr['delivery_stage'] = ctx['package_stage']
            auto = (worksheet or {}).get('automation') or {}
            if isinstance(auto, dict) and auto.get('content_read_complete') is True:
                # A genuinely absent direction must remain unknown, not be
                # invented merely to satisfy the legacy input schema. This
                # only enables material-gap disposition, never numerical PASS.
                lr['_automatic_review_material_gap_checks'] = [gap.get('check_id')
                    for gap in auto.get('material_gaps', []) if isinstance(gap, dict)
                    and gap.get('section') == 'core' and gap.get('read_complete') is True]
                g03 = next((check for check in (lr.get('content_gates') or {}).get('checks', [])
                    if check.get('id') == 'G03'), {})
                if g03.get('review_complete') is True and g03.get('observed_status') in {'manual', 'fail'}:
                    lr['_automatic_review_material_gap_checks'].append('G03')
            if sr and (sr.get('harbor') or {}).get('gpu_selection') is not None:
                shared=sr['harbor']['gpu_selection']
                if 'gpu_selection' in lr and lr['gpu_selection']!=shared:
                    raise ValueError('standard与legacy的实际选卡依据不一致。')
                lr['gpu_selection']=copy.deepcopy(shared)
        result = migration.assess(root, sr, lr, out)
        actual = migration.all_rows(result)
        indexed = {r['id']:copy.deepcopy(r) for r in actual}
        rows = [indexed.get(key, missing_row(key)) for key in CORE_IDS]
        annotate_deployment_causes(rows,result.get('standard_components',{}).get('harbor',{}),sr)
        annotate_resource_causes(rows,result.get('standard_components',{}).get('resources',{}),result.get('standard_components',{}).get('harbor',{}),sr)
        migration.write_report(result, out)
        return {'decision':result.get('decision'), 'complete':bool(result.get('review_completed')), 'checks':rows,
            'raw':result, 'errors':result.get('input_and_review_errors', []),
            'waivers':[r for r in result.get('standard_findings', []) if r.get('effective_status')=='pass_with_waivers']}
    native, code = migration.run_standard(root, sr, out)
    components, errors = migration.inspect_components(root, sr, native)
    rows = standard_rows(native, components,sr)
    complete = bool(native.get('review', {}).get('completed')) and not errors and all(r.get('status') in SUCCESS | {'fail'} for r in rows)
    if native.get('inspection_error'):
        errors.append({'component':'standard', 'message':native['inspection_error']})
        complete=False
    return {'decision':native.get('summary', {}).get('decision'), 'complete':complete, 'checks':rows,
        'raw':native, 'components':components, 'errors':errors, 'exit_code':code, 'waivers':[]}


def format_review(root, worksheet, ctx):
    fr = copy.deepcopy((worksheet or {}).get('format'))
    if fr is None and ctx['mode']=='legacy-waiver' and isinstance((worksheet or {}).get('legacy'),dict):
        fr=copy.deepcopy(worksheet['legacy'])
        fr['stage']='format_repair'
    if fr is not None and not isinstance(fr, dict):
        raise ValueError('format必须是内部F01–F07审阅对象。')
    settings = fr if fr is not None else {}
    settings['deployment_profile'] = ctx['provider']
    settings['delivery_stage'] = ctx['package_stage']
    sr = (worksheet or {}).get('standard') or {}
    if not isinstance(sr,dict): sr={}
    hr=sr.get('harbor') if isinstance(sr.get('harbor'),dict) else {}
    shared=hr.get('gpu_selection')
    if shared is not None:
        if 'gpu_selection' in settings and settings['gpu_selection']!=shared:
            raise ValueError('standard与format的实际选卡依据不一致。')
        settings['gpu_selection']=copy.deepcopy(shared)
    settings.setdefault('task_root', hr.get('task_root'))
    assessed = fmt.assess(root, settings, _with_inventory=True) if fr is not None else None
    scan = (assessed or {}).pop('_inventory', None)
    if scan is None:
        scan = fmt.inventory(root, settings)
    indexed = {r['id']:r for r in (assessed or {}).get('checks', [])}
    rows=[]
    for key,title in fmt.CHECKS.items():
        row=copy.deepcopy(indexed.get(key, {'id':key,'title':title,'status':'manual','summary':'格式内容尚未实际审完。','evidence':[]}))
        faults=[i for i in scan['issues'] if i['owner']==key]
        if faults:
            row.update(status='fail', summary='；'.join(i['summary'] for i in faults), automatic_findings=faults)
        rows.append(row)
    return {'checks':rows,'scan':scan,'complete':bool(assessed and assessed.get('decision')!='ERROR'),
        'errors':(assessed or {}).get('input_and_review_errors', []),'template':fmt.review_template(scan)}


def module_errors(result):
    values = result.get('validation_errors', result.get('errors', []))
    return values if isinstance(values, list) else [str(values)]


def apply_engineering(result, engineering, *, shared_key='engineering_review'):
    """Share one semantic review across existing owners; do not add a gate.

    Pattern observations are never blockers. Only evidenced reviewer findings
    enter the owner row, after legacy reconciliation, so current defects cannot
    accidentally inherit a historical waiver. Delivery/scope claims are notes.
    """
    section = result['sections']['core']
    section[shared_key] = engineering
    indexed = {r['id']: r for r in section['checks']}
    for group in engineering.get('checks', []):
        owner = indexed.get(group.get('owner_id'))
        if owner is None:
            continue
        ref = group['name'] if shared_key=='engineering_review' else shared_key+'/'+group['name']
        owner.setdefault('engineering_refs', []).append(ref)
        required = group.get('required_for_static_completion', True)
        problems = group.get('problems', []) if not group.get('delivery_notes_only') else []
        if problems or required and group.get('status') in {'unreviewed', 'evidence_limited'}:
            owner.setdefault('before_engineering', {
                k: copy.deepcopy(owner[k]) for k in ('status','summary','evidence','review_complete') if k in owner})
            owner['evidence'] = list(dict.fromkeys(owner.get('evidence', []) + group.get('evidence', [])))
            if problems:
                converted = [{**copy.deepcopy(p), 'summary':p['reason'],
                    'responsibility':p.get('responsibility',p.get('owner', 'author')),
                    'related_checks':list(dict.fromkeys([group['owner_id']] + p.get('related_checks', [])))} for p in problems]
                owner.setdefault('engineering_findings', []).extend(converted)
                owner['status'] = 'fail'
                owner['summary'] = (owner.get('summary','') + '；工程审阅：' +
                    '；'.join(p['reason'] for p in problems)).strip('；')
            elif owner.get('status') != 'fail':
                owner.update(status='manual', summary=owner.get('summary','') + '；工程审阅：' + group['summary'])
            owner['review_complete'] = (owner.get('review_complete') is not False and group.get('review_complete') is True)
        if required and not group.get('review_complete'):
            section['complete'] = False
            owner['review_complete'] = False
    for error in engineering.get('errors', []):
        if error.get('required'):
            section['complete'] = False
            section.setdefault('errors', []).append({'component':shared_key, **error})


def summarize(sections, *, mode):
    """Failures win, incomplete coverage cannot be promoted by another PASS."""
    failures=[]; unfinished=[]; waivers=[]
    for section_name, section in sections.items():
        for row in section.get('checks', []):
            status=row.get('status')
            if status=='fail': failures.append({'section':section_name,**row})
            elif status in {'pass_with_waivers','waived'}: waivers.append({'section':section_name,**row})
            elif status not in SUCCESS and row.get('required_for_static_completion', True): unfinished.append({'section':section_name,**row})
        if not section.get('complete', False):
            unfinished.append({'section':section_name,'id':'COVERAGE','status':'review_not_finished','summary':'本模块实际审阅或底稿校验未完成。','errors':section.get('errors',[])})
    decision='FAIL' if failures else 'REVIEW_INCOMPLETE' if unfinished else 'PASS_WITH_WAIVERS' if waivers else 'PASS'
    return {'decision':decision,'review_complete':not unfinished,'failure_count':len(failures),'unfinished_count':len(unfinished),
        'waiver_count':len(waivers),'failed_checks':failures,'unfinished_checks':unfinished,'waived_checks':waivers,
        'scope':'完整静态审查及已交证据复核；不代表本次Harbor实跑或平台入库验收。','mode':mode}


def apply_current_waivers(root, current, worksheet, ctx):
    """Only an existing authorized historical-proof gap can close CS05 review.

    Confirmed current <=50 failure, unread content and all other current defects
    stay unchanged. This is reviewer disposition, never a new author schema.
    """
    resolutions=(worksheet or {}).get('current_resolutions',[])
    if not isinstance(resolutions,list):
        current.setdefault('errors',[]).append('current_resolutions必须是逐原因数组。'); return
    if resolutions and ctx['mode']!='legacy-waiver':
        current.setdefault('errors',[]).append('standard模式不得使用历史证明豁免。'); return
    used=set()
    for resolution in resolutions:
        try:
            if not isinstance(resolution,dict) or resolution.get('id')!='CS05' or 'CS05' in used:
                raise ValueError('只允许对CS05已有历史证明缺口作一次精确处理。')
            row=next(r for r in current.get('checks',[]) if r['id']=='CS05')
            if (row.get('status')!='review' or resolution.get('waiver_reason')!='legacy_runtime_proof_gap'
                or resolution.get('scope')!='historical_records_only' or resolution.get('content_review_complete') is not True
                or resolution.get('new_record_requirement_only') is not True or not resolution.get('summary')):
                raise ValueError('只能在已读完旧材料后豁免新增历史证明缺口；不能免当前确定失败或省略内容。')
            import audit_legacy_task
            audit_legacy_task.references(root,resolution.get('evidence'),'CS05具体历史证明缺口',content=True)
            row.update(original_status='review',status='pass_with_waivers',waiver=copy.deepcopy(resolution),
                summary='已审原材料；仅旧记录新增主响应证明缺口获免，不宣称已证明新L0。')
            used.add('CS05')
        except (ValueError,TypeError,KeyError,OSError,StopIteration) as exc:
            current.setdefault('errors',[]).append(str(exc))


def classified_actions(result):
    actions={'author':[],'platform':[],'coordination':[],'reviewer':[]}
    for row in result.get('summary',{}).get('failed_checks',[]):
        key=row.get('section','')+'/'+str(row.get('id'))
        explicit = [finding for finding in row.get('findings', []) if isinstance(finding, dict)
            and (finding.get('final_effect') == 'blocking' or
                 finding.get('effect') == 'unwaived' and finding.get('kind') == 'substantive')]
        causes = (list(row.get('automatic_findings') or []) + list(row.get('format_root_causes') or [])
            + explicit + list(row.get('engineering_findings') or []))
        if not causes:
            causes = [row]
        elif row.get('automatic_findings') and row.get('review_status')=='fail' and not explicit:
            causes.append(row)
        for cause in causes:
            code=str(cause.get('code','')).lower()
            default_owner='author_or_platform' if result.get('context',{}).get('package_stage')=='runtime' else 'author'
            owner=cause.get('responsibility',row.get('responsibility',default_owner))
            if code in {'published_image_required','gpu_actual_unsupported'}:
                owner='platform'
            if owner in {'platform','platform_or_author','author_or_platform','not_established'}:
                bucket='platform' if owner=='platform' else 'coordination'
            elif owner=='reviewer': bucket='reviewer' if row.get('failure_kind')=='reviewer_input' else 'coordination'
            else: bucket='author'
            action=cause.get('remediation') or cause.get('action') or row.get('remediation') or row.get('action') or '按已确认问题定位修改位置并保留复查依据。'
            if code=='published_image_required':
                action='平台完成镜像构建/发布并配置当前运行包，核对实际拉取和启动；不要求外部专家回填内部tag。'
            item={'id':key,'code':code,'summary':cause.get('summary',cause.get('message',row.get('summary',''))),
                'evidence':cause.get('evidence',row.get('evidence',[])),'action':action,
                'related_checks':list(dict.fromkeys([key] + cause.get('related_checks', []))),
                'acceptance_evidence':cause.get('acceptance_evidence',row.get('acceptance_evidence',''))}
            matching=next((old for old in actions[bucket] if code and old.get('code')==code and old.get('evidence')==item['evidence'] and old['action']==action),None)
            if matching:
                if key not in matching['related_checks']: matching['related_checks'].append(key)
                if item['summary'] not in matching['summary']: matching['summary']+='；'+item['summary']
            else: actions[bucket].append(item)
    return actions


def assess(root, worksheet=None, *, out, mode=None, provider=None, stage=None,
           intake_cohort=None, rollout_policy=None, target_level=None):
    import current_standard_review
    import supplement_review
    import engineering_review
    import delivery_contract_review
    root,out=Path(root).resolve(),Path(out).resolve()
    if out==root or out.is_relative_to(root): raise ValueError('输出必须在待检题包外。')
    ctx=context(worksheet,mode,provider,stage,intake_cohort=intake_cohort,rollout_policy=rollout_policy,target_level=target_level)
    out.mkdir(parents=True,exist_ok=True)
    files=core.inventory(root)
    result={'schema_version':1,'version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'stage':'complete_unified_review',
        'context':ctx,'source_root':str(root),'task_code_executed':False,'platform_runtime_status':'not_executed',
        'early_exit_content_gates':False,'sections':{},'processing_errors':[]}
    def independently(name,operation,expected=()):
        try:
            result['sections'][name]=operation()
        except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
            result['sections'][name]={'checks':[missing_row(key,str(exc)) for key in expected], 'complete':False,'errors':[str(exc)]}
            result['processing_errors'].append({'component':name,'message':str(exc)})
    independently('core',lambda:run_core(root,worksheet,ctx,out/'base'),CORE_IDS)
    independently('format',lambda:format_review(root,worksheet,ctx),fmt.CHECKS)
    scan=result['sections'].get('format',{}).get('scan',{})
    cfg=scan.get('config')
    if cfg is None:
        source_review=(worksheet or {}).get('standard') or {}
        hr=source_review.get('harbor') if isinstance(source_review,dict) else {}
        task=hr.get('task_root') if isinstance(hr,dict) else None
        cfg=core.task_config(root/task) if isinstance(task,str) else None
    independently('current_standard',lambda:current_standard_review.audit(root,files=files,config=cfg,
        review=(worksheet or {}).get('current_standard'),stage=ctx['package_stage']),[key for key,_ in current_standard_review.CHECKS])
    known=scan.get('issues',[])
    metadata=cfg.get('metadata',{}) if isinstance(cfg,dict) else {}
    metadata=metadata if isinstance(metadata,dict) else {}
    task_id=ctx.get('task_id') or metadata.get('task_id') or metadata.get('id') or metadata.get('name') or '本题'
    independently('supplement',lambda:supplement_review.apply_review(root,(worksheet or {}).get('supplement'),
        package_stage=ctx['package_stage'],known_findings=known,task_id=task_id))
    # Adapters expose the full original module payload alongside common rows.
    current=result['sections'].get('current_standard',{})
    apply_current_waivers(root,current,worksheet,ctx)
    if 'complete' not in current:
        current['complete']=not module_errors(current) and all(r.get('status') in SUCCESS|{'fail'} or not r.get('required_for_static_completion',True) for r in current.get('checks',[]))
    current.setdefault('errors',module_errors(current))
    for row in current.get('checks',[]):
        row.setdefault('summary','；'.join(map(str,row.get('problems',[])+row.get('limitations',[]))) or '在现有材料范围内完成本项核对。')
        row.setdefault('remediation',{'CS03':'允许txt、JSON或双文件；按JSON优先及已有真实读取链核对，不因双文件要求返修。','CS04':'明确主分及实际候选/评分对应；兼容旧数值字段，不以诊断任意数字或无效值冒充成绩。','CS05':'按实际退出原因核对做题主Agent响应；由控制运行预算/会话的一方处理，不用工具次数或补造记录替代。'}.get(row.get('id'),''))
    sup=result['sections'].get('supplement',{})
    if 'checks' not in sup:
        coverage=sup.get('coverage',{})
        sup['checks']=[]
        values=coverage.items() if isinstance(coverage,dict) else [(r.get('id'),r) for r in coverage]
        for key,raw in values:
            row=copy.deepcopy(raw)
            row.update(id=key, original_coverage_status=raw.get('status'), summary=raw.get('reason',''))
            state=raw.get('status')
            row['status']='fail' if state=='findings' else 'pass' if state=='reviewed_no_finding' else 'not_applicable' if state in {'not_applicable','skipped_no_runtime'} else 'review'
            row['required_for_static_completion']=not (raw.get('scope')=='platform_runtime' and state=='evidence_limited' and raw.get('coverage_record_complete') is True)
            linked=[f for f in sup.get('findings',[]) if key in f.get('check_ids',[f.get('check_id')])]
            row['findings']=linked
            if linked:
                row['summary']='；'.join(str(f.get('summary',f.get('root_cause','已确认问题'))) for f in linked)
                row['responsibility']=linked[0].get('owner','author_or_platform')
                row['remediation']='；'.join(str(f.get('action','')) for f in linked)
            sup['checks'].append(row)
    if 'complete' not in sup:
        sup['complete']=bool(sup.get('static_review_complete') and sup.get('coverage_record_complete') and sup.get('provided_runtime_review_complete')) and not module_errors(sup)
    sup.setdefault('errors',module_errors(sup))
    try:
        engineering=engineering_review.audit(root, (worksheet or {}).get('engineering'),
            task_root=scan.get('task_root'),config=cfg,stage=ctx['package_stage'])
    except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        engineering={'observations':[], 'claims':{}, 'errors':[{'group':'score_paths','required':True,'error':str(exc)}],
            'checks':[{'name':'score_paths','owner_id':'H04','status':'unreviewed','summary':str(exc),
                'required_for_static_completion':True,'review_complete':False}], 'executed_task':False}
    apply_engineering(result, engineering)
    try:
        contract=delivery_contract_review.audit(root, (worksheet or {}).get('delivery_contract'),
            context=ctx,task_root=scan.get('task_root'),config=cfg)
    except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        contract={'observations':[], 'claims':{}, 'errors':[{'group':'task_contract','required':True,'error':str(exc)}],
            'checks':[{'name':'task_contract','owner_id':'QA11','status':'unreviewed','summary':str(exc),
                'required_for_static_completion':True,'review_complete':False}], 'executed_task':False}
    apply_engineering(result, contract,shared_key='delivery_contract_review')
    for section in result['sections'].values():
        for row in section.get('checks', []):
            if row.get('status') == 'fail' and row.get('format_root_causes'):
                row['summary_before_derived_failure'] = row.get('summary', '')
                row['summary'] = '关联格式检查失败：' + '；'.join(str(c.get('summary',c.get('message',''))) for c in row['format_root_causes'])
    result['summary']=summarize(result['sections'],mode=ctx['mode'])
    result['decision']=result['summary']['decision']
    result['coverage_counts']={name:len(section.get('checks',[])) for name,section in result['sections'].items()}
    result['actions']=classified_actions(result)
    result['high_priority_advisories']=high_priority_advisories(result)
    result['scope_note']='研究质量原G01–G03保留为并行检查，不作前置短路门控；其失败不阻止其余可安全检查。集合类型覆盖不属于本单题检查。'
    result['templates']={'context':ctx,'standard':migration.standard_template(),
        'format':result['sections'].get('format',{}).get('template'),
        'legacy':result['sections'].get('core',{}).get('raw',{}).get('review_template') if ctx['mode']=='legacy-waiver' else None,
        'current_standard':current_standard_review.template() if hasattr(current_standard_review,'template') else {},
        'supplement':supplement_review.template() if hasattr(supplement_review,'template') else {}, 'current_resolutions':[],
        'engineering':engineering_review.template(),
        'delivery_contract':delivery_contract_review.template(),
        'automation':{'content_read_complete':False,'material_gaps':[]}}
    return result


def cell(value):
    return str(value).replace('|','\\|').replace('\n',' ').replace('\r',' ')


def row_summary(row):
    if row.get('status') == 'fail' and row.get('format_root_causes'):
        text = '关联格式检查失败：' + '；'.join(str(cause.get('summary', cause.get('message', '')))
            for cause in row['format_root_causes'])
        if row.get('engineering_findings'):
            text += '；工程：' + '；'.join(p['summary'] for p in row['engineering_findings'])
    else:
        text = row.get('summary', row.get('reason', ''))
    if row.get('engineering_refs'):
        text += '〔共享工程事实：' + ', '.join(row['engineering_refs']) + '〕'
    return text


def engineering_lines(result):
    facts=result.get('sections',{}).get('core',{}).get('engineering_review',{})
    if not facts:
        return []
    lines=['','## 共享工程事实（归入既有项目，不增加门控）','',
        '| 视角 | 状态 | 主责 | 已审结论 |','|---|---|---|---|']
    for group in facts.get('checks',[]):
        lines.append('| '+' | '.join(cell(x) for x in (group.get('name'),group.get('status'),group.get('owner_id'),group.get('summary')))+' |')
        for branch, detail in group.get('branches',{}).items():
            lines.append('| '+cell(group['name']+'/'+branch)+' | 已记录 | '+cell(group.get('owner_id'))+' | '+cell(detail.get('summary'))+'；结果：'+cell(detail.get('outcome'))+' |')
    for group in facts.get('checks',[]):
        if group.get('evidence'):
            lines += ['',group['name']+' 证据：'+cell(group['evidence'])]
        for advisory in group.get('advisories',[]):
            lines += ['非阻断说明：'+cell(advisory.get('reason'))+'；处理：'+cell(advisory.get('remediation'))]
        if group.get('limitations'):
            lines += ['读取/覆盖限制：'+cell(group['limitations'])]
    lines += ['', '成绩与采用范围（unknown/null 表示现有依据不足，不能改写原始分）：',
        json.dumps(facts.get('claims',{}),ensure_ascii=False),
        '静态观察与完整内部说明见 report.json；观察、镜像名或关键词不直接判 FAIL。外部交付绑定仅单列平台事项。']
    return lines


def high_priority_advisories(result):
    items=[]
    core_section=result.get('sections',{}).get('core',{})
    for source in ('engineering_review','delivery_contract_review'):
        for group in core_section.get(source,{}).get('checks',[]):
            for finding in group.get('advisories',[]):
                if finding.get('priority')=='high':
                    items.append({'owner_id':group.get('owner_id'),'group':group.get('name'),**copy.deepcopy(finding)})
    return items


def contract_lines(result):
    facts=result.get('sections',{}).get('core',{}).get('delivery_contract_review',{})
    if not facts:return []
    lines=['','## 题面、锚点与批次适用口径（既有编号的共享事实）','',
        '| 视角 | 主责 | 状态 | 具体结论 |','|---|---|---|---|']
    for group in facts.get('checks',[]):
        lines.append('| '+' | '.join(cell(v) for v in (group.get('name'),group.get('owner_id'),group.get('status'),group.get('summary')))+' |')
        if group.get('evidence'):lines.append('| 证据 | | | '+cell(group['evidence'])+' |')
    lines += ['', '静态结论、实际评测及历史准入分别记录：',json.dumps(facts.get('claims',{}),ensure_ascii=False),
        '历史“有分或超时且轨迹审阅通过”的准入不认证Verifier。暂不实施“一小时超时无分就不通过”；仅缺分数不新增FAIL或材料不完整要求，仍据实记录Verifier未被验证。已确认的评分、实现或输出缺陷继续保留。']
    for advisory in result.get('high_priority_advisories',high_priority_advisories(result)):
        lines += ['','高优整改建议（非体积硬门）：'+cell(advisory.get('reason')),
            '依据：'+cell(advisory.get('evidence',[])),'建议：'+cell(advisory.get('remediation'))]
    return lines


def decision_text(value):
    return {
        'MATERIALS_INCOMPLETE': 'MATERIALS_INCOMPLETE（材料不完整，未通过）',
        'REVIEW_INCOMPLETE': 'REVIEW_INCOMPLETE（自动检查未完成，不是专家材料结论）',
    }.get(value, value)


def material_gap_lines(result, *, expert_only=False):
    gaps = result.get('missing_materials') or []
    if expert_only:
        gaps = [gap for gap in gaps if gap.get('owner') in {'author', 'coordination'}]
    lines = []
    if gaps:
        lines += ['', '## 材料不完整：自动审查已定位的缺口', '']
        for gap in gaps:
            lines += [
                '- ' + cell(gap.get('check_id', gap.get('id', ''))) + '：' + cell(gap.get('missing_material', '')),
                '  原因：' + cell(gap.get('why_needed', '')),
                '  已核对来源：' + cell(gap.get('reviewed_evidence', [])),
                '  补充动作：' + cell(gap.get('next_action', '')),
                '  责任：' + cell(gap.get('owner', 'coordination')),
            ]
    return lines


def review_completion(result):
    """Expose process completion independently of a confirmed failure verdict."""
    states = []
    for value in ((result.get('summary') or {}).get('review_complete'),
                  (result.get('automation_final') or {}).get('review_process_complete')):
        if isinstance(value, bool):
            states.append(value)
    if result.get('decision') == 'REVIEW_INCOMPLETE' or False in states:
        return False
    return True if states and all(states) else None


def render(result):
    lines=['# AutoResearch 完整兼容质检报告','', '结论：'+decision_text(result['decision']),
        '范围：'+result.get('summary',{}).get('scope','本次检查未完成。'),
        '模式：'+result.get('context',{}).get('mode','unknown')+'；平台运行：未执行；原提交只读。','']
    ctx=result.get('context',{})
    lines += ['适用口径：intake_cohort='+str(ctx.get('intake_cohort','unspecified'))+
        '；rollout_policy='+str(ctx.get('rollout_policy','按source/runtime阶段'))+
        '；target_level='+str(ctx.get('target_level','未声明，不认证高级别'))+'。','']
    completed = review_completion(result)
    if completed is False:
        lines += ['完成状态：检查尚未完成。已确认的问题仍保留；其他未结项由审阅Agent继续读取或修正，不能当作专家材料缺失。','']
    elif completed is True:
        lines += ['完成状态：本轮材料审阅已完成；已确认缺陷、材料缺口和平台运行覆盖限制分别见下文。','']
    names={'core':'完整内容、21项、Harbor与两轨','format':'F01–F07当前格式','current_standard':'本次兼容检查','supplement':'算法增量A与平台专项B'}
    for name,section in result.get('sections',{}).items():
        if name=='supplement' and section.get('algorithm_output'):
            algorithm=section['algorithm_output'];difficulty=algorithm.get('difficulty',{})
            lines += ['## 算法A单题主结论（仅六类范围，不代替统一总评）','',algorithm['main_conclusion'],
                '覆盖范围：'+str(algorithm.get('coverage_basis')),
                '难度（不参与验收）：'+str(difficulty.get('judgment') or difficulty.get('status'))+'；'+str(difficulty.get('reason',''))]
            for note in algorithm.get('coverage_limitations',[]): lines.append('覆盖限制：'+str(note))
            if difficulty.get('basis'): lines.append('难度依据：'+json.dumps(difficulty['basis'],ensure_ascii=False))
            if difficulty.get('evidence'): lines.append('难度证据：'+cell(difficulty['evidence']))
            for finding in algorithm.get('evidence_details',[]):
                lines += ['','A完整证据明细：',json.dumps(finding,ensure_ascii=False,indent=2)]
        lines += ['## '+names.get(name,name),'','| 项目 | 状态 | 具体发现 | 证据 |','|---|---|---|---|']
        for row in section.get('checks',[]):
            state = '材料不完整' if row.get('status') == 'material_incomplete' else row.get('status')
            lines.append('| '+' | '.join(cell(x) for x in [row.get('id'),state,row_summary(row), '；'.join(map(str,row.get('evidence',[])))])+' |')
        for row in section.get('checks',[]):
            if isinstance(row.get('waiver'),dict):
                waiver=row['waiver']
                lines += ['',str(row.get('id'))+'具体历史处理：',
                    '原状态：'+str(row.get('original_status'))+'；原因：'+str(waiver.get('waiver_reason')),
                    str(waiver.get('summary','')),'适用范围：'+str(waiver.get('scope')),
                    '依据：'+'；'.join(map(str,waiver.get('evidence',[]))),
                    '原限制保留：'+cell(row.get('limitations',[]))]
        if section.get('errors'): lines += ['','内部审阅未完成原因：'+cell(section['errors'])]
    lines += engineering_lines(result)
    lines += contract_lines(result)
    lines += material_gap_lines(result)
    lines += ['','## 具体整改与处理','']
    for owner,title in [('author','专家需返修'),('platform','平台需处理'),('coordination','双方协调'),('reviewer','自动检查内部问题')]:
        lines += ['### '+title,'']
        actions=result.get('actions',classified_actions(result))[owner]
        for row in actions:
            lines += ['- '+row['id']+'：'+cell(row['summary']),'  证据：'+cell(row['evidence']),'  处理：'+cell(row['action'])]
            if row.get('acceptance_evidence'): lines.append('  复检依据：'+cell(row['acceptance_evidence']))
        if not actions: lines.append('无已确认事项。')
    lines += ['','## 覆盖限制与豁免','',result.get('scope_note',''),
        '所有适用原判、逐原因豁免、资源、时长、指纹、原始分数及会话发现均保留在report.json和base/；不把历史免责当成绩有效。本版不设置NOP验收项。',
        '平台准备/实际运行/回传未执行或材料未提供时按阶段留痕，不据此虚构作者缺陷，也不宣称已运行成功。']
    base=result.get('sections',{}).get('core',{}).get('raw',{})
    if base:
        lines += ['','## 基础完整审阅、逐seed成绩与具体历史处理','',
            '以下为基础组件底稿，原判与豁免过程完整保留；组件结论不能代替本文顶部统一总评。']
        if result.get('automation_final', {}).get('applied'):
            lines.append('以下原始内部诊断来自自动结案前；已归入材料不完整的旧未结提示仅供追溯，不是当前待人工事项。当前完成态及具体缺口见统一总评和材料不完整清单。')
        if result.get('context',{}).get('mode')=='legacy-waiver':
            details=migration.render(base)
        else:
            details=core.compact_markdown(base)
        details=details.replace('前置内容门槛','研究质量检查（并行、不提前退出）').replace('研究三门','研究质量三项').replace('前置三门','研究质量三项').replace('待补充核验','质检员尚未完成内容审阅').replace('待核验','未完成内容审阅')
        details=details.replace('# 质检结论：','# 基础组件结论（不含新标准和增量，不代表统一总评）：').replace('本轮结论：','基础与历史处理子结论：')
        if result.get('automation_final', {}).get('applied'):
            details=details.replace('质检流程需继续完成的部分','原始内部诊断（自动结案前，非当前待办）')
        lines.append(details)
    return '\n'.join(lines)+'\n'


def expert_text(result):
    completed = review_completion(result)
    scope = ('本轮已审材料，其他检查尚未完成，未运行题包。' if completed is False
             else '完整静态审查及已有证据复核，未运行题包。')
    lines=['本轮结论：'+decision_text(result['decision'])+'。范围：'+scope,'']
    groups=result.get('actions',classified_actions(result))
    for title,owner in [('专家需返修','author'),('平台需处理','platform'),('双方协调','coordination')]:
        lines += [title+'：']
        for row in groups[owner]:
            lines += [row['id']+'：'+cell(row['summary']),'证据：'+'；'.join(map(str,row['evidence'])),'处理：'+cell(row['action']),'']
            if row.get('acceptance_evidence'): lines += ['复检依据：'+cell(row['acceptance_evidence']),'']
        if not groups[owner]: lines.append('无已确认事项。')
    if completed is False:
        lines += ['','自动检查未完成：已确认缺陷保留；其余部分需要由审阅 Agent 继续读取或修正内部审核数据，工具或检查中断不作为专家缺材料结论。']
    engineering=result.get('sections',{}).get('core',{}).get('engineering_review',{})
    notes=[g for g in engineering.get('checks',[]) if g.get('delivery_notes_only') and g.get('advisories')]
    if notes:
        lines += ['','交付绑定说明（非专家源码返修，不否定已有成绩）：']
        for group in notes:
            lines += [cell(a.get('reason'))+'；平台/交付动作：'+cell(a.get('remediation')) for a in group['advisories']]
    advisories=result.get('high_priority_advisories',high_priority_advisories(result))
    if advisories:
        lines += ['','高优整改建议（未恢复CS02体积硬门）：']
        for advisory in advisories:
            lines += [cell(advisory.get('owner_id'))+'：'+cell(advisory.get('reason')),
                '证据：'+cell(advisory.get('evidence',[])),'建议：'+cell(advisory.get('remediation'))]
    lines += material_gap_lines(result, expert_only=True)
    platform_gaps = [gap for gap in result.get('missing_materials', []) if gap.get('owner') == 'platform']
    if platform_gaps:
        lines += ['', '平台材料缺口（不要求专家补内部运行材料）：']
        for gap in platform_gaps:
            lines += ['- ' + cell(gap.get('check_id', '')) + '：' + cell(gap.get('missing_material', '')),
                '  平台动作：' + cell(gap.get('next_action', ''))]
    raw=result.get('sections',{}).get('core',{}).get('raw',{})
    overview=raw.get('overview') or {}
    comparison=overview.get('baseline_reference') or {}
    if comparison:
        lines += ['','已复核正式方法与原始跑分：', 'Baseline：'+str(comparison.get('baseline_method','')),
            'Reference：'+str(comparison.get('reference_method','')),
            '正式成对原值：'+json.dumps(comparison.get('paired_runs',[]),ensure_ascii=False)]
    waived=result.get('sections',{}).get('core',{}).get('waivers',[])
    if waived:
        lines += ['','本次具体历史处理：']
        for row in waived:
            lines += ['- '+str(row.get('owner'))+' / '+str(row.get('waiver_reason'))+'：'+str(row.get('resolution',{}).get('summary',row.get('summary','')))]
    for section in result.get('sections',{}).values():
        for row in section.get('checks',[]):
            if isinstance(row.get('waiver'),dict):
                waiver=row['waiver']
                lines += ['- '+str(row.get('id'))+' / '+str(waiver.get('waiver_reason'))+'：'+str(waiver.get('summary','')),
                    '  原状态：'+str(row.get('original_status'))+'；范围：'+str(waiver.get('scope')),
                    '  依据：'+'；'.join(map(str,waiver.get('evidence',[])))]
    if result.get('summary',{}).get('waiver_count'):
        lines += ['','豁免不改写原始事实或受影响分数状态，全部细项见完整报告。']
    return '\n'.join(lines)+'\n'


def write_report(result,out):
    out=Path(out)
    template=result.pop('templates',None)
    dump(out/'report.json',result)
    for name in ['report.md','report.txt']:
        fmt.atomic_write(out/name,render(result))
    fmt.atomic_write(out/'return_to_expert.txt',expert_text(result))
    if template is not None: dump(out/'review_template.json',template)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--mode',choices=MODES)
    parser.add_argument('--provider',choices=PROVIDERS)
    parser.add_argument('--package-stage',choices=('source','runtime'))
    parser.add_argument('--intake-cohort',choices=INTAKE_COHORTS)
    parser.add_argument('--rollout-policy',choices=ROLLOUT_POLICIES)
    parser.add_argument('--target-level',choices=TARGET_LEVELS)
    parser.add_argument('--automation-final', action='store_true',
        help='Agent完成全部读取后自动终审；精确材料缺口不转人工，按材料不完整输出。')
    args=parser.parse_args(argv)
    source,out=args.source.expanduser().resolve(),args.out_dir.expanduser().resolve()
    if out==source or source.is_dir() and out.is_relative_to(source): parser.error('输出必须在原包外。')
    if args.review and args.review.expanduser().resolve().is_relative_to(out): parser.error('内部底稿请放在输出目录外，防止终稿覆盖输入。')
    worksheet, root = None, None
    try:
        worksheet=load_review(args.review)
        kind=audit_task.inspect_source_kind(source)
        if kind=='directory': root=source
        else:
            out.mkdir(parents=True,exist_ok=True)
            core.cleanup_previous_evidence(out)
            root=Path(tempfile.mkdtemp(prefix='evidence-',dir=out))
            facts=audit_task.safe_extract_zip(source,root)
            if facts.unsafe_entries: raise ValueError('归档包含不安全条目：'+'；'.join(facts.unsafe_entries[:3]))
        result=assess(root,worksheet,out=out,mode=args.mode,provider=args.provider,stage=args.package_stage,
            intake_cohort=args.intake_cohort,rollout_policy=args.rollout_policy,target_level=args.target_level)
        result['source']={'path':str(source),'kind':kind}
        if kind=='zip': result['source']['sha256']=facts.sha256
        if args.automation_final:
            import automation_final
            result=automation_final.finalize(result,worksheet,root)
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,zipfile.BadZipFile) as exc:
        result={'version':VERSION,'decision':'REVIEW_INCOMPLETE','stage':'input_or_review_error','task_code_executed':False,
            'platform_runtime_status':'not_executed','processing_errors':[str(exc)],'sections':{},'is_task_rejection':False}
    write_report(result,out)
    print(json.dumps({'decision':result['decision'],'stage':result['stage'],'report_json':str(out/'report.json'),'report_txt':str(out/'report.txt')},ensure_ascii=False))
    return 0 if result['decision'] in {'PASS','PASS_WITH_WAIVERS'} else 1 if result['decision'] in {'FAIL','MATERIALS_INCOMPLETE'} else 2


if __name__=='__main__':
    from audit_current import main as current_main
    raise SystemExit(current_main())
