#!/usr/bin/env python3
"""One current standard, read-only evidence review, two final acceptance results.

The current Skill Agent performs the semantic reading. This trusted program
validates its evidence and the independent static contracts; no task code runs.
"""
from __future__ import annotations
import argparse
import codecs
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import zipfile

import audit_format_repair as fmt
import automation_final
import delivery_contract_review as delivery
import engineering_review as engineering

VERSION='0.5.0-current.1'
SKILL_ROOT=Path(__file__).resolve().parents[1]
RULES={
    **dict.fromkeys(('harbor_format','oracle','dependency_lock','reward_protocol','hard_gate',
        'task_contract','artifact_binding','public_dev','private_boundary','resource_limit',
        'normalization','solver_turns','solvability','baseline_health','runtime_failure','data_assets',
        'image_size','runtime_stability','collection_diversity'),'L0'),
    **dict.fromkeys(('method_space','constraint_enforcement','score_stability','shortcut_resistance'),'L1'),
    **dict.fromkeys(('reference_calibration','research_iteration','adversarial_rollout'),'L2'),
    **dict.fromkeys(('platform_scope','legacy_schema','third_party_source','research_duration'),'scope')}
OWNERS={'author','platform','coordination','inspection'}
# Existing project scientific checks remain strict; they are not relabelled L0.
# The Nov 7 meeting changed the four delivery protocols and routing, not these gates.
PROJECT_REQUIRED={'method_space','reference_calibration','third_party_source'}
STATIC_CODES={'CORE_FILE_MISSING','TOML_PARSE','TABLE_SHAPE','SEPARATE_REQUIRED','RESOURCE_CONFIG',
    'CPU_WITH_GPU','AGENT_ENVIRONMENT_MISSING','TEST_ENTRY_MISSING','IMAGE_TYPE','IMAGE_FORMAT',
    'DOCKERFILE_FROM','ARTIFACTS_TYPE','ARTIFACTS_SOURCE','ARTIFACTS_UNCOVERED'}
TEXT_SUFFIXES={'.py','.sh','.bash','.md','.txt','.json','.jsonl','.toml','.yaml','.yml','.log','.csv','.tsv','.xml','.html','.cfg','.ini','.lock',
    '.c','.cc','.cpp','.h','.hpp','.rs','.cu','.cuh','.js','.jsx','.ts','.tsx','.r','.jl','.java','.ipynb','.sql','.sha256'}

def dump(path,value):
    fmt.atomic_write(Path(path),json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def read_json(path):
    def reject(token):raise ValueError('Nonfinite JSON constant: '+token)
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    obj=json.loads(Path(path).read_text(),parse_constant=reject,object_pairs_hook=unique)
    if not isinstance(obj,dict):raise ValueError('Internal review must be an object')
    return obj

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def materials(root):
    root=Path(root).resolve();rows=[]
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Unsafe source link: '+str(path))
        if not path.is_file():continue
        with path.open('rb') as stream:prefix=stream.read(4096)
        try:codecs.getincrementaldecoder('utf-8')().decode(prefix,final=False);utf8=True
        except UnicodeError:utf8=False
        text=(path.suffix.lower() in TEXT_SUFFIXES or utf8 and b'\0' not in prefix)
        row={'path':path.relative_to(root).as_posix(),'size':path.stat().st_size,'sha256':digest(path),'kind':'text' if text else 'binary'}
        if text:
            count=0;last=b''
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):count+=block.count(b'\n');last=block[-1:]
            row['lines']=count+int(last not in {b'',b'\n'})
        rows.append(row)
    return rows

def route_map():
    mapping=read_json(SKILL_ROOT/'references/current-check-map.json')['checks']
    expected=set().union(*automation_final.EXPECTED.values())
    if len(mapping)!=90 or {r['id'] for r in mapping}!=expected:raise ValueError('Trusted current check map must contain exactly the 90 IDs')
    return {r['id']:r for r in mapping}

def unpack(source,destination):
    destination.mkdir(parents=True,exist_ok=False)
    if zipfile.is_zipfile(source):
        fmt.unpack(source,destination)
        return destination
    if not tarfile.is_tarfile(source):raise ValueError('Expected directory, ZIP or TAR archive')
    seen=set();total=0
    with tarfile.open(source) as archive:
        for member in archive:
            relative=Path(member.name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in member.name or not (member.isfile() or member.isdir()):
                raise ValueError('Archive contains a link, special file or path escape')
            key=relative.as_posix().casefold().rstrip('/')
            if key in seen:raise ValueError('Duplicate archive entry: '+member.name)
            seen.add(key);total+=member.size
            if len(seen)>fmt.MAX_FILES or total>fmt.MAX_UNPACKED:raise ValueError('Archive exceeds trusted extraction limits; use a safe directory input')
            path=destination/relative
            if member.isdir():path.mkdir(parents=True,exist_ok=True);continue
            path.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(member) as stream,path.open('xb') as target:shutil.copyfileobj(stream,target,1024*1024)
    return destination

def template(scan,files):
    routes=route_map()
    checks=[]
    for section,ids in automation_final.EXPECTED.items():
        for code in sorted(ids):
            checks.append({'id':code,'section':section,'scope':routes[code]['current_scope'],
                'guidance':routes[code]['nonblocking_scope'],'status':'unreviewed','summary':'','evidence':[],'findings':[]})
    return {'schema_version':1,'standard':'current-2189','checks':checks,
        'engineering':engineering.template(),'delivery_contract':delivery.template(),
        'coverage':{'content_read_complete':False,'algorithm_a_independent_reread':False,
            'sources':[{'path':r['path'],'sha256':r['sha256'],'disposition':'unreviewed',
                        'read_ranges':[]} for r in files]},
        'notes':['Internal worksheet completed by the Skill Agent, never an expert form.',
                 'No mode, cohort, provider or target-level selection changes the standard.',
                 'Findings use rule/reason/remediation/evidence/responsibility; rule level and blocking are computed by the trusted checker.',
                 'Current ungraded norms and L0 block. Existing project G01/G03 and platform dependency-source rules remain required; other L1/L2 findings are recommendations.',
                 'Unknown deployment provider alone is a platform coverage note; do not invent support or blame the expert.',
                 'Read all supplied sessions and all formally declared seeds; no fixed two-model/eight-field/10-hour legacy gate.']}

def located_refs(root,values,inventory,*,positioned=False):
    if not isinstance(values,list) or not values:raise ValueError('Existing evidence references are required')
    result=[]
    for ref in values:
        if not isinstance(ref,str) or not ref.strip():raise ValueError('Evidence must be nonempty strings')
        if positioned and not re.search(r':\d+(?:-\d+)?$|#(?:/|L\d|field=|\$\.)',ref):raise ValueError('Finding evidence needs a line or field position')
        record=inventory.get(ref)
        if record is None or record['kind']!='binary':engineering._resolve_evidence(root,ref)
        result.append(ref)
    return list(dict.fromkeys(result))

def issue(message,check_id=None,evidence=None):
    return {'check_id':check_id,'responsibility':'inspection','reason':message,
            'remediation':'质检端修复读取、内部底稿或工具后重审；不是专家题包缺陷。','evidence':evidence or []}

def module_rule(value):
    """Only native, typed protocol facts may infer their rule automatically."""
    if value.get('rule') in RULES:return value['rule']
    code=value.get('code','')
    if code in {'current.oracle_entry_location','current.oracle_entry_missing','current.oracle_implementation_location'}:return 'oracle'
    if code=='current.dependency_lock':return 'dependency_lock'
    if code=='current.gate_penalty':return 'hard_gate'
    if code in {'current.formal_reward_file_choice','current.json_reward_main_key','current.selected_run_dual_reward',
                'current.selected_run_json_main_key'}:return 'reward_protocol'
    if code=='runtime.selected_current_reward_invalid':return 'reward_protocol'
    if code=='normalization.confirmed_hardware_anchor_mismatch':return 'normalization'
    return value.get('rule')

def current_module_review(review):
    """A caller's old blocking flag cannot reinstate an obsolete hard gate."""
    result=copy.deepcopy(review)
    if not isinstance(result,dict):return result
    groups=result.get('groups',result)
    if not isinstance(groups,dict):return result
    for group in groups.values():
        if not isinstance(group,dict):continue
        for finding in group.get('findings',[]) if isinstance(group.get('findings',[]),list) else []:
            if isinstance(finding,dict) and finding.get('rule') in RULES:
                finding['blocking']=required_rule(finding['rule'])
    return result

def required_rule(rule):
    return RULES[rule]=='L0' or rule in PROJECT_REQUIRED

def validate_coverage(root,review,files):
    errors=[];coverage=review.get('coverage') or {}
    if not isinstance(coverage,dict):return [issue('coverage不是对象。')]
    if coverage.get('content_read_complete') is not True:errors.append(issue('未确认完整阅读已交材料。'))
    if coverage.get('algorithm_a_independent_reread') is not True:errors.append(issue('原算法A的独立复读尚未完成。'))
    supplied=coverage.get('sources',[])
    if not isinstance(supplied,list):return errors+[issue('coverage.sources不是数组。')]
    indexed={}
    for row in supplied:
        if not isinstance(row,dict) or not isinstance(row.get('path'),str) or row.get('path') in indexed:errors.append(issue('阅读来源有重复或结构错误。'));continue
        indexed[row.get('path')]=row
    for record in files:
        row=indexed.get(record['path'],{})
        if row.get('sha256')!=record['sha256']:errors.append(issue('来源版本未绑定：'+record['path']));continue
        if record['kind']=='binary':
            if row.get('disposition')!='binary_manifest':errors.append(issue('二进制资产未按清单核对：'+record['path']))
            continue
        ranges=row.get('read_ranges',[])
        if row.get('disposition')!='read' or not isinstance(ranges,list):errors.append(issue('文本尚未完整阅读：'+record['path']));continue
        intervals=[]
        try:
            for pair in ranges:
                if not isinstance(pair,list) or len(pair)!=2 or any(isinstance(v,bool) or not isinstance(v,int) for v in pair):raise ValueError()
                lo,hi=pair
                if not 1<=lo<=hi<=max(1,record['lines']):raise ValueError()
                intervals.append((lo,hi))
            end=0
            for lo,hi in sorted(intervals):
                if lo>end+1:break
                end=max(end,hi)
            if record['lines'] and end<record['lines']:errors.append(issue('文本阅读区间有遗漏：'+record['path']))
        except ValueError:errors.append(issue('文本阅读区间格式错误：'+record['path']))
    if set(indexed)!=set(r['path'] for r in files):errors.append(issue('阅读来源集合与本题实际材料不一致。'))
    return errors

def inspect(root,review=None):
    root=Path(root).resolve();files=materials(root);by_path={r['path']:r for r in files}
    scan=fmt.inventory(root,{'deployment_profile':'unknown','delivery_stage':'source'})
    routes=route_map();out={'version':VERSION,'standard':'Xpert current revision2189; required norms/L0 and existing project/platform requirements',
        'source_root':str(root),'task_root':scan['task_root'],'task_code_executed':False,'platform_runtime_status':'not_executed',
        'findings':[],'recommendations':[],'inspection_issues':[],'platform_notes':list(scan.get('platform_observations',[])),
        'checks':[],'coverage_counts':{k:len(v) for k,v in automation_final.EXPECTED.items()},'facts':{},
        'review_template':template(scan,files),'source_manifest':files}
    if review is None:
        out.update(operation='prepared',final_result_available=False)
        return out
    # Blank preparation worksheets are never another result inside the final report.
    out.pop('review_template',None)
    if not isinstance(review,dict):raise ValueError('Internal review must be an object')
    if review.get('schema_version')!=1 or isinstance(review.get('schema_version'),bool):
        out['inspection_issues'].append(issue('内部底稿schema_version不是当前版本1。'))
    if review.get('standard')!='current-2189':
        out['inspection_issues'].append(issue('内部底稿未绑定当前唯一标准current-2189。'))
    out['inspection_issues']+=validate_coverage(root,review,files)
    supplied=review.get('checks',[])
    if not isinstance(supplied,list):supplied=[];out['inspection_issues'].append(issue('checks不是数组。'))
    index={}
    for row in supplied:
        if not isinstance(row,dict) or row.get('id') not in routes or row['id'] in index:
            out['inspection_issues'].append(issue('检查ID未知、重复或格式错误。'));continue
        index[row['id']]=row
    for section,ids in automation_final.EXPECTED.items():
        for code in sorted(ids):
            raw=index.get(code,{})
            row={'id':code,'section':section,'scope':routes[code]['current_scope'],'summary':raw.get('summary',''),
                 'evidence':[],'findings':[],'recommendations':[],'result':'不通过'}
            errors=[]
            values=raw.get('findings',[])
            if not isinstance(values,list):
                errors.append(issue('findings不是数组。',code));values=[]
            # Preserve an already established defect even if another cell in the
            # same worksheet row is malformed. Inspection errors never erase facts.
            for value in values:
                    try:
                        if not isinstance(value,dict) or value.get('rule') not in RULES:raise ValueError('缺少当前规范rule枚举。')
                        if not all(engineering._specific(value.get(k)) for k in ('reason','remediation')):raise ValueError('发现需具体原因和整改。')
                        if value.get('responsibility') not in OWNERS:raise ValueError('发现需责任归属。')
                        evidence=located_refs(root,value.get('evidence'),by_path,positioned=True)
                        fact={**copy.deepcopy(value),'check_id':code,'level':RULES[value['rule']],
                              'blocking':required_rule(value['rule']),'evidence':evidence,
                              'requirement_source':'project_continuation' if value['rule'] in PROJECT_REQUIRED else 'current_standard'}
                        row['findings' if fact['blocking'] else 'recommendations'].append(fact)
                    except (ValueError,OSError,UnicodeError,TypeError) as exc:errors.append(issue(str(exc),code))
            try:
                if raw.get('status') not in {'pass','fail','not_applicable','advisory'}:raise ValueError('该项内容审阅未提交有效判断。')
                if not engineering._specific(raw.get('summary')):raise ValueError('需要本题具体判断，不能填泛化通过。')
                row['evidence']=located_refs(root,raw.get('evidence'),by_path)
                if raw.get('status')=='fail' and not values:raise ValueError('失败必须有具体当前规范发现，不能沿用旧原判。')
            except (ValueError,OSError,UnicodeError,TypeError) as exc:errors.append(issue(str(exc),code))
            row['result']='不通过' if row['findings'] or errors else '通过'
            out['inspection_issues']+=errors;out['checks'].append(row)
            out['findings']+=row['findings'];out['recommendations']+=row['recommendations']
    # Concrete static defects cannot be removed by a semantic PASS.
    for fault in scan['issues']:
        code=fault['code']
        current=(code in STATIC_CODES or code.startswith('PATH_')
                 or code=='TASK_DIRECTORY_MISSING' and any(str(p).endswith('/tests') or str(p)=='tests' for p in fault.get('evidence',[])))
        if not current:
            out['platform_notes'].append({**fault,'note':'旧格式观察，仅供当前语义核对；不凭旧固定目录、Compose或未知底座规则自动拒收。'})
            continue
        fact={'check_id':fault['owner'],'rule':'harbor_format','level':'L0','blocking':True,
            'reason':fault['summary'],'remediation':'按当前Harbor配置、文件路径及提交物契约修复。',
            'responsibility':'author','evidence':fault.get('evidence',[]),'code':fault['code']}
        out['findings'].append(fact)
    for label,module,notes in [('engineering',engineering,'engineering'),('delivery_contract',delivery,'delivery_contract')]:
        try:
            kwargs={'task_root':scan['task_root'],'config':scan['config']}
            if label=='engineering':kwargs['stage']='source'
            result=module.audit(root,current_module_review(review.get(label)),**kwargs)
            result.pop('template',None)
            result.pop('review_template',None)
            out['facts'][label]=result
            for error in result.get('errors',[]):
                if error.get('required',True):out['inspection_issues'].append(issue(str(error.get('error',error))))
            for group in result.get('checks',[]):
                for value in group.get('problems',[])+group.get('advisories',[]):
                    rule=module_rule(value)
                    if rule not in RULES:
                        out['inspection_issues'].append(issue('事实发现未绑定当前rule枚举：'+label+'/'+group['name'],group['owner_id'],value.get('evidence',[])))
                        continue
                    fact={**value,'check_id':group['owner_id'],'rule':rule,'level':RULES[rule],
                          'blocking':required_rule(rule),'responsibility':value.get('responsibility','author'),
                          'requirement_source':'project_continuation' if rule in PROJECT_REQUIRED else 'current_standard'}
                    out['findings' if fact['blocking'] else 'recommendations'].append(fact)
                if group.get('required_for_static_completion',True) and not group.get('review_complete'):
                    out['inspection_issues'].append(issue('内部事实审阅未完成：'+label+'/'+group['name'],group['owner_id']))
                elif group.get('status')=='evidence_limited' and group.get('required_for_static_completion',True):
                    scoped=[f for f in group.get('advisories',[]) if f.get('rule')=='platform_scope']
                    details=group.get('details',{})
                    limited_keys={key for key,value in details.items() if isinstance(value,dict) and value.get('status')=='evidence_limited'} if isinstance(details,dict) else set()
                    allowed_scope=(label=='delivery_contract' and group['name']=='infra_capabilities' and scoped
                        and not group.get('problems') and limited_keys=={'environment_compatibility'})
                    if allowed_scope:
                        out['platform_notes'].append({'group':group['name'],'summary':group['summary'],
                            'note':'已完整审源码；明确列出的平台动态能力尚未实测，不单独阻断静态。'})
                    else:
                        out['inspection_issues'].append(issue('内部审阅需定位该项真正缺少的必要材料或平台范围：'+label+'/'+group['name'],group['owner_id']))
        except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
            out['inspection_issues'].append(issue(label+'检查器异常：'+str(exc)))
    # The parent summary is based only on this current verdict, never old FAILs.
    failures={f.get('check_id') for f in out['findings']}|{e.get('check_id') for e in out['inspection_issues'] if e.get('check_id')}
    harbor_ids={'H01','H02','H03','H04','H05','F01','F02','F03','F04','F05','F06','F07'}
    harbor_rules={'harbor_format','oracle','dependency_lock','reward_protocol','hard_gate','artifact_binding','private_boundary','runtime_failure'}
    harbor_fail=any(f.get('rule') not in {'method_space','reference_calibration'} and
        (f.get('check_id') in harbor_ids or f.get('rule') in harbor_rules) for f in out['findings'])
    harbor_issue=any(e.get('check_id') in harbor_ids for e in out['inspection_issues'])
    for row in out['checks']:
        if row['id'] in failures:row['result']='不通过'
        if row['id']=='QA17':
            row['result']='不通过' if row['findings'] or harbor_fail or harbor_issue else '通过'
            row['summary']='仅汇总本次Harbor格式、交付与独立评分事实；不把科研或批次分类问题误记为Harbor缺陷。'
    out['decision']='FAIL' if out['findings'] or out['inspection_issues'] else 'PASS'
    out['result']='不通过' if out['decision']=='FAIL' else '通过'
    out['final_result_available']=True
    try:changed=materials(root)!=files
    except (OSError,ValueError):changed=True
    if changed:
        out['inspection_issues'].append(issue('检查期间来源文件发生变化；需绑定稳定版本重新审阅。'))
        out['decision']='FAIL';out['result']='不通过'
    out['inspection']={'content_read_complete':not out['inspection_issues'],'issue_count':len(out['inspection_issues'])}
    return out

def repair_actions(report):
    grouped={owner:[] for owner in OWNERS}
    seen={}
    for fact in report.get('findings',[])+report.get('inspection_issues',[]):
        owner=fact.get('responsibility','author')
        if owner=='author_or_platform':owner='coordination'
        if owner not in grouped:owner='coordination'
        reason=fact.get('reason',str(fact));fix=fact.get('remediation','定位当前原因并修复。')
        code=fact.get('code','')
        native=code in {'current.gate_penalty','current.dependency_lock','current.oracle_entry_missing',
            'current.oracle_entry_location','current.oracle_implementation_location',
            'normalization.confirmed_hardware_anchor_mismatch'}
        key=(code,) if native else (owner,reason,fix,tuple(fact.get('evidence',[])))
        if key in seen:
            previous=seen[key]
            previous['evidence']=list(dict.fromkeys(previous.get('evidence',[])+fact.get('evidence',[])))
            previous['related_check_ids']=list(dict.fromkeys(previous['related_check_ids']+[fact.get('check_id')]))
            continue
        projected=copy.deepcopy(fact);projected['related_check_ids']=[fact.get('check_id')]
        seen[key]=projected;grouped[owner].append(projected)
    return grouped

def render(report,expert=False):
    lines=['本轮结论：'+report['result'],'标准：当前题目规范及L0必需要求，延续原项目科学、资源及平台要求；没有历史豁免或人工版本选择。',
           '范围：只读静态审阅及已交证据复核；本次未运行Docker或Harbor。','']
    actions=repair_actions(report)
    for owner,title in [('author','专家返修'),('platform','平台处理'),('coordination','双方核对'),('inspection','质检端处理')]:
        if not actions[owner]:continue
        lines.append(title+'：')
        for f in actions[owner]:
            checks=' / '.join(str(c) for c in f.get('related_check_ids',[]) if c) or '检查流程'
            lines+=['- '+checks+'：'+f['reason'],
                    '  修改：'+f.get('remediation','定位当前原因并修复。'),
                    '  证据：'+'；'.join(f.get('evidence',[]))]
    if expert and not actions['author']:lines.append('本轮没有已确认的专家代码/文件返修项；其他责任事项见上列。')
    if not expert:
        lines+=['','逐项检查（保留原项目科学要求；不将其他高级等级义务扩为默认硬门）：','| 项目 | 结果 | 当前事实 |','|---|---|---|']
        for row in report['checks']:
            lines.append('| '+row['id']+' | '+row['result']+' | '+row['summary'].replace('|','\\|').replace('\n',' ')+' |')
        if report.get('recommendations'):
            lines+=['','建议及验证范围：']
            for r in report['recommendations']:lines.append('- '+r.get('reason',r.get('summary',str(r))))
    return '\n'.join(lines)+'\n'

def write(report,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    dump(out/'report.json',report)
    fmt.atomic_write(out/'report.md',render(report));fmt.atomic_write(out/'report.txt',render(report))
    fmt.atomic_write(out/'return_to_expert.txt',render(report,True))

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--review',type=Path);parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args(argv);source=args.source.expanduser().resolve();out=args.out_dir.expanduser().resolve()
    if source==out or out.is_relative_to(source) or source.is_relative_to(out):parser.error('输入与输出目录必须分开。')
    if args.prepare_only and args.review:parser.error('prepare-only与review不可同时使用。')
    if not args.prepare_only and not args.review:parser.error('由Skill Agent先prepare-only，再读取材料并使用review完成终审。')
    if args.review:
        selected_review=args.review.expanduser().resolve()
        if source.is_dir() and selected_review.is_relative_to(source):parser.error('内部底稿不得写入专家来源目录。')
        if selected_review in {out/name for name in ('report.json','report.md','report.txt','return_to_expert.txt')}:
            parser.error('正式输出不得覆盖内部底稿；请使用独立review文件。')
    out.mkdir(parents=True,exist_ok=True)
    try:
        if args.prepare_only:
            for name in ('report.json','report.md','report.txt','return_to_expert.txt'):
                stale=out/name
                if stale.exists() or stale.is_symlink():stale.unlink()
        root=source if source.is_dir() else unpack(source,out/'inspection'/'source')
        review=read_json(args.review) if args.review else None
        report=inspect(root,review)
        if args.prepare_only:
            control=out/'inspection';control.mkdir(exist_ok=True)
            dump(control/'review_template.json',report['review_template'])
            dump(control/'materials.json',{k:report[k] for k in ('version','source_root','task_root','source_manifest','coverage_counts')})
            dump(control/'observations.json',report)
            print(json.dumps({'operation':'prepared','final_result_available':False,'source_root':str(root),
                'review_template':str(control/'review_template.json'),'materials':str(control/'materials.json')},ensure_ascii=False))
            return 0
        write(report,out)
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,zipfile.BadZipFile,tarfile.TarError) as exc:
        report={'version':VERSION,'decision':'FAIL','result':'不通过','checks':[],'findings':[],
            'inspection_issues':[issue('质检端未能完成有效核对：'+str(exc))],'recommendations':[],
            'inspection':{'content_read_complete':False},'task_code_executed':False,'platform_runtime_status':'not_executed'}
        write(report,out)
    print(json.dumps({'decision':report['decision'],'result':report['result'],'report':str(out/'report.json')},ensure_ascii=False))
    return 0 if report['decision']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
