function brandReplace(text) {
  return String(text).replace(/gemini/gi, 'Geniview');
}

const I18N = {
  zh: {
    login_subtitle: '视频动作分析与标注平台',
    login_meta: '登录后进入系统主页，统一查看检测任务、结果统计与标注审核。',
    login_welcome: '欢迎回来',
    login_username: '用户名',
    login_password: '密码',
    login_button: '登录',
    logout: '退出',
    close: '关闭',
    loading: '加载中...',
    nav_detection: '视觉检测',
    nav_review: '结果查看',
    nav_users: '用户管理',
    nav_settings: '设置',
    nav_calculator: '费用计算器',
    nav_short_detection: '检',
    nav_short_review: '看',
    nav_short_users: '管',
    nav_short_settings: '设',
    nav_short_calculator: '算',
    not_logged_in: '未登录',
    edit_action: '编辑动作',
    add_action: '新增动作',
    delete_action: '删除动作',
    cannot_delete_last_action: '仅剩一个动作时不可删除',
    user_create: '新增用户',
    user_username: '用户名',
    user_password: '密码',
    user_email: '邮箱',
    user_api_key: 'API Key',
    user_role: '角色',
    role_user: '普通用户',
    role_admin: '管理员',
    user_model: '模型',
    user_status: '状态',
    status_active: '启用',
    status_inactive: '停用',
    cancel: '取消',
    save: '保存',
    edit_index: '序号',
    action_index: '序号',
    action_thumb: '帧',
    export_csv: '导出 CSV',
    revision_history: '修订历史',
    revision_none: '暂无修订记录',
    revision_restore: '恢复',
    revision_restore_confirm: '确定回滚到该版本？当前内容会先自动存入修订历史。',
    revision_restored: '已回滚到指定修订版本',
    revision_load_failed: '修订历史加载失败: {error}',
    no_result_selected: '请先选择结果文件',
    vanva_title: '增值 / 非增值统计 (VA / NVA)',
    vanva_va: '增值 (VA)',
    vanva_nva: '非增值 (NVA)',
    vanva_nnva: '必要非增值 (NNVA)',
    vanva_unknown: '未标注',
    vanva_total: '总时长',
    vanva_actions_unit: '个动作',
    vanva_empty: '当前结果无增值/非增值或时间数据',
    revoke_sessions: '强制下线',
    revoke_sessions_title: '吊销该用户全部登录会话，立即强制下线',
    revoke_sessions_confirm: '确定强制下线用户「{username}」？其所有登录会话将立即失效。',
    revoke_sessions_done: '已强制下线「{username}」，吊销会话 {count} 个',
    revoke_sessions_failed: '强制下线失败: {error}',
    action_desc: '动作描述',
    therblig_type: '动素类型',
    is_process: '是否加工',
    is_move: '是否搬运',
    is_check: '是否检查',
    is_wait: '是否等待',
    is_store: '是否存储',
    sop_steps: 'SOP 操作步骤',
    value_added: '增值/非增值',
    hands: '左右手',
    variation_source: '波动来源',
    time_range: '时间区间',
    left_hand: '左手状态',
    right_hand: '右手状态',
    start_time_earlier_than_prev: '开始时间不能早于上一个动作的开始时间 ({time})',
    end_time_later_than_next: '结束时间不能晚于下一个动作的结束时间 ({time})',
    start_time_later_than_end_time: '开始时间不能晚于结束时间',
    estimated_duration: '预估耗时 (s)',
    auto_calculate: '自动计算',
    notify_title: 'Geniview 通知',
    ok: '确定',
    detect_running_hint: '正在对视频进行检测分析，请稍等...',
    settings_title: '系统设置',
    settings_general: '通用设置',
    settings_theme: '主题模式',
    theme_dark: '深色模式',
    theme_light: '浅色模式',
    settings_theme_tip: '切换后立即生效，并记住你的选择。',
    settings_language: '语言',
    lang_zh: '中文',
    lang_en: 'English',
    settings_language_tip: '切换后立即生效，并记住你的选择。',
    settings_version_label: '当前版本:',
    settings_version_loading: 'loading...',
    detection_title: '视觉检测任务',
    detection_new_task: '新建任务',
    detection_fps_label: 'FPS (每秒采样帧数)',
    detection_select_video: '选择视频',
    upload_to_data: '上传视频到 data/:',
    choose_file: '选择文件',
    file_not_selected: '未选择文件',
    upload: '上传',
    detect_model_label: '模型',
    detect_model_default: 'GeniviewK2.5 (长文本/视觉增强)',
    upload_video_label: '视频上传',
    preprocess_video_label: '视频预处理',
    estimate_cost: '预估费用',
    estimate_cost_label: '预估费用:',
    cost_based_on: '基于:',
    cost_seconds_video: 's 视频 | 输入 ',
    cost_tokens_out_sep: ' | 输出 ',
    cost_tokens_think_sep: ' | 思考 ',
    estimate_out_tokens: '预计输出 tokens',
    estimate_think_tokens: '预计思考 tokens',
    cost_details: '查看详细公式与中间量',
    cost_formula_1:
      '1) 采样帧数 N = ceil(T × fps) = ceil(<span id="costT">0</span> × <span id="costFps">0</span>) = <span id="costFrames">0</span>',
    cost_formula_2:
      '2) 视觉输入 tokens V = N × k = <span id="costFrames2">0</span> × <span id="costTokPerFrame">258</span> = <span id="costVisionTokens">0</span>',
    cost_formula_3:
      '3) 输入 tokens In = V + P = <span id="costVisionTokens2">0</span> + <span id="costPromptTokens">0</span> = <span id="costInTokens">0</span>',
    cost_formula_4:
      '4) 计费输出 tokens Out_bill = Out + Think = <span id="costOutTokens">0</span> + <span id="costThinkTokens">0</span> = <span id="costBillableOutTokens">0</span>',
    cost_formula_5:
      '5) 输入费用 C_in = In / 1e6 × price_in = <span id="costInTokens2">0</span> / 1e6 × <span id="costPriceIn">0</span> = $<span id="costInUSD">0.0000</span>',
    cost_formula_6:
      '6) 输出费用 C_out = Out_bill / 1e6 × price_out = <span id="costBillableOutTokens2">0</span> / 1e6 × <span id="costPriceOut">0</span> = $<span id="costOutUSD">0.0000</span>',
    cost_formula_total:
      '总费用 C = C_in + C_out = $<span id="costTotalUSD2">0.0000</span>',
    cost_formula_note:
      '说明：P 为固定提示词/结构化输出等估算 tokens；k 为每帧视觉 token 估算系数；Think 为“思考/推理 tokens”估算（按输出单价计）。',
    start_detect: '开始检测与标注',
    prepare_text: '准备中...',
    collapse_log: '折叠日志',
    expand_log: '展开日志',
    detect_preview_alt: '实时检测预览',
    review_title: '结果查看',
    review_select_result: '选择结果文件...',
    review_select_video: '选择视频文件...',
    refresh: '刷新',
    review_no_video: '未选择视频',
    review_actions: '动作 <span class="pill" id="actionCount">0</span>',
    time_range: '时间段',
    stat_total_actions: '动作总数',
    stat_action_types: '动作种类',
    stat_avg_duration: '平均时长',
    stat_distribution: '动作种类分布 (柱状图)',
    process_advice: '工艺流程改进建议',
    no_advice: '暂无建议',
    overview_title: '工序概览 (Overview)',
    station_compare_title: '工位动作时间对比',
    deep_dive_title: '深度诊断发现 (Deep Dive Findings)',
    kaizen_title: '改善机会 (Kaizen Opportunities)',
    users_title: '用户管理',
    user_list: '用户列表',
    user_actions: '操作',
    user_created_at: '创建时间',
    user_data_size: '数据量',
    no_users: '暂无用户',
    calculator_title: '费用计算器',
    calculator_header: 'Token 费用预估',
    calculator_model: '模型选择',
    calculator_model_default: 'GeniviewK 2.5 - 默认',
    calculator_input_tokens: '输入 Token 数量',
    calculator_output_tokens: '输出 Token 数量',
    calculator_start: '开始计算',
    calculator_formula_title: '计算公式 (GeniviewK 2.5):',
    calculator_price_input: 'Input: ¥0.004 / 1k tokens',
    calculator_price_output: 'Output: ¥0.021 / 1k tokens',
    calculator_input_cost: '输入费用',
    calculator_output_cost: '输出费用',
    calculator_total_cost: '总费用',
    login_failed: '登录失败',
    network_error: '网络错误',
    load_failed: '加载失败',
    load_error: '加载出错: {error}',
    role_admin: '管理员',
    role_user: '普通用户',
    status_inactive: '停用',
    status_active: '启用',
    upload_in_progress: '正在上传视频...',
    not_logged_in_or_expired: '未登录或登录已过期',
    upload_timeout: '网络连接失败或上传超时 (HTTP 0)',
    load_failed_with_error: '加载失败: {error}',
    edit: '编辑',
    user_list_load_failed: '用户列表加载失败: {error}',
    user_edit: '编辑用户',
    user_new_password_optional: '新密码 (留空不变)',
    save_failed: '保存失败',
    select_video_placeholder: '请选择视频...',
    expand_or_collapse_log: '展开日志',
    select_video_for_duration: '请先选择视频以获取时长',
    select_file_first: '请先选择文件',
    uploading: '上传中...',
    preprocessing_video: '正在预处理视频...',
    extract_frames_failed: '截取图片失败',
    preprocess_done: '视频预处理完成，共 {count} 帧',
    upload_success: '上传成功!',
    upload_failed: '上传失败: {error}',
    upload_error: '上传出错: {error}',
    select_video_first: '请先选择视频',
    processing_detect: '正在处理中 (Geniview 分析 + 视觉标注)...',
    task_start_log: '[{time}] 开始任务...\n视频: {video}\n模型: {model}\nFPS: {fps}\n',
    request_params_log: '请求参数: {params}\n',
    start_failed: '启动失败: {error}',
    detect_progress: '正在检测: {current} / {total} 帧 ({pct}%)',
    detect_progress_request: '正在请求模型: {current} / {total} 次 ({pct}%)',
    task_complete: '[{time}] 任务完成!\nJSON: {json}\nVideo: {video}\n',
    jump_to_review: '正在跳转到结果查看页...',
    process_failed_check_log: '处理失败，请查看日志',
    no_matching_result: '未找到名称前缀相同的结果文件：{name}',
    no_content: '（无内容）',
    avg_duration_seconds: '平均时长 (s)',
    no_advice_data: '暂无建议数据',
    unknown_json_format: '未知的 JSON 格式（缺少 actions）。keys: {keys}',
    load_result_failed: '加载结果失败: {error}',
    unknown_error: 'Unknown error',
    result_not_found: '未找到对应的结果文件，请重新选择视频。',
    save_success: '保存成功',
    save_failed_with_error: '保存失败: {error}',
    load_failed_with_status: '加载失败: {url} ({status})',
    page_load_failed: '页面加载失败: {error}',
    reason: '原因',
    // 阶段 2：组织层级
    nav_org: '组织管理',
    nav_short_org: '组',
    scope_label: '作用域',
    scope_loading: '加载中...',
    scope_all_lines: '全部产线',
    scope_no_project: '暂无项目',
    org_title: '组织管理',
    org_projects: '项目列表',
    org_create_project: '新建项目',
    org_no_projects: '暂无项目',
    org_project_code: '项目编号',
    org_project_name: '项目名称',
    org_project_desc: '描述',
    org_status: '状态',
    status_archived: '归档',
    org_my_role: '我的角色',
    org_created_at: '创建时间',
    org_actions: '操作',
    org_manage_lines: '产线',
    org_manage_members: '成员',
    org_edit: '编辑',
    org_lines: '产线列表',
    org_create_line: '新建产线',
    org_no_lines: '暂无产线',
    org_line_code: '产线编号',
    org_line_name: '产线名称',
    org_process_desc: '工艺描述',
    org_sop: '产线 SOP',
    org_sop_content: 'SOP 内容（该产线分析时注入，优先于全局 SOP）',
    org_sop_configured: '已配置',
    org_sop_empty: '未配置',
    org_members: '成员管理',
    org_member_username: '用户名',
    org_member_username_ph: '用户名',
    org_member_role: '项目角色',
    org_member_user_role: '系统角色',
    org_no_members: '暂无成员',
    org_add_member: '添加成员',
    org_remove: '移除',
    org_member_removed: '成员已移除',
    role_owner: '负责人',
    role_editor: '编辑者',
    role_viewer: '观察者',
    org_edit_project: '编辑项目',
    org_edit_line: '编辑产线',
    org_save_success: '保存成功',
    org_sop_saved: 'SOP 已保存',
    org_load_failed: '加载失败',
    org_remove_member_confirm: '确定将 {username} 移出该项目？',
    org_lines_of: '产线'
  },
  en: {
    login_subtitle: 'Video Action Analysis & Annotation Platform',
    login_meta:
      'Log in to access detection tasks, result analytics, and annotation reviews in one place.',
    login_welcome: 'Welcome Back',
    login_username: 'Username',
    login_password: 'Password',
    login_button: 'Sign In',
    logout: 'Sign Out',
    close: 'Close',
    loading: 'Loading...',
    nav_detection: 'Detection',
    nav_review: 'Results',
    nav_users: 'Users',
    nav_settings: 'Settings',
    nav_calculator: 'Cost Calculator',
    nav_short_detection: 'D',
    nav_short_review: 'R',
    nav_short_users: 'U',
    nav_short_settings: 'S',
    nav_short_calculator: 'C',
    not_logged_in: 'Not Logged In',
    edit_action: 'Edit Action',
    add_action: 'Add Action',
    delete_action: 'Delete Action',
    cannot_delete_last_action: 'Cannot delete the last action',
    user_create: 'Create User',
    user_username: 'Username',
    user_password: 'Password',
    user_email: 'Email',
    user_api_key: 'API Key',
    user_role: 'Role',
    role_user: 'User',
    role_admin: 'Admin',
    user_model: 'Model',
    user_status: 'Status',
    status_active: 'Active',
    status_inactive: 'Inactive',
    cancel: 'Cancel',
    save: 'Save',
    edit_index: 'Index',
    action_index: 'Index',
    action_thumb: 'Frame',
    export_csv: 'Export CSV',
    revision_history: 'Revisions',
    revision_none: 'No revisions yet',
    revision_restore: 'Restore',
    revision_restore_confirm: 'Restore this version? The current content will be snapshotted first.',
    revision_restored: 'Restored to the selected revision',
    revision_load_failed: 'Failed to load revisions: {error}',
    no_result_selected: 'Select a result file first',
    vanva_title: 'VA / NVA Breakdown',
    vanva_va: 'Value-added (VA)',
    vanva_nva: 'Non-value-added (NVA)',
    vanva_nnva: 'Necessary NVA (NNVA)',
    vanva_unknown: 'Unlabeled',
    vanva_total: 'Total',
    vanva_actions_unit: 'actions',
    vanva_empty: 'No VA/NVA or time data in this result',
    revoke_sessions: 'Force Sign Out',
    revoke_sessions_title: 'Revoke all login sessions of this user immediately',
    revoke_sessions_confirm: 'Force sign out "{username}"? All their sessions will be revoked.',
    revoke_sessions_done: '"{username}" signed out, {count} session(s) revoked',
    revoke_sessions_failed: 'Force sign out failed: {error}',
    action_desc: 'Action Description',
    therblig_type: 'Therblig Type',
    is_process: 'Processing',
    is_move: 'Transport',
    is_check: 'Inspection',
    is_wait: 'Waiting',
    is_store: 'Storage',
    sop_steps: 'SOP Steps',
    value_added: 'Value-Added/Non-Value',
    hands: 'Hands',
    variation_source: 'Variation Source',
    time_range: 'Time Range',
    left_hand: 'Left Hand',
    right_hand: 'Right Hand',
    start_time: 'Start Time (s)',
    end_time: 'End Time (s)',
    start_time_earlier_than_prev: 'Start time cannot be earlier than previous action start time ({time})',
    end_time_later_than_next: 'End time cannot be later than next action end time ({time})',
    start_time_later_than_end_time: 'Start time cannot be later than end time',
    estimated_duration: 'Estimated Duration (s)',
    auto_calculate: 'Auto',
    notify_title: 'Geniview Notice',
    ok: 'OK',
    detect_running_hint: 'Analyzing the video, please wait...',
    settings_title: 'System Settings',
    settings_general: 'General Settings',
    settings_theme: 'Theme',
    theme_dark: 'Dark',
    theme_light: 'Light',
    settings_theme_tip: 'Applies immediately and remembers your choice.',
    settings_language: 'Language',
    lang_zh: '中文',
    lang_en: 'English',
    settings_language_tip: 'Applies immediately and remembers your choice.',
    settings_version_label: 'Current Version:',
    settings_version_loading: 'loading...',
    detection_title: 'Detection Task',
    detection_new_task: 'New Task',
    detection_fps_label: 'FPS (frames per second)',
    detection_select_video: 'Select Video',
    upload_to_data: 'Upload video to data/:',
    choose_file: 'Choose File',
    file_not_selected: 'No file selected',
    upload: 'Upload',
    detect_model_label: 'Model',
    detect_model_default: 'GeniviewK2.5 (Long Text / Vision Enhanced)',
    upload_video_label: 'Video Upload',
    preprocess_video_label: 'Video Preprocessing',
    estimate_cost: 'Estimate Cost',
    estimate_cost_label: 'Estimated Cost:',
    cost_based_on: 'Based on:',
    cost_seconds_video: 's video | Input ',
    cost_tokens_out_sep: ' | Output ',
    cost_tokens_think_sep: ' | Thinking ',
    estimate_out_tokens: 'Estimated output tokens',
    estimate_think_tokens: 'Estimated thinking tokens',
    cost_details: 'Show detailed formula',
    cost_formula_1:
      '1) Sample frames N = ceil(T × fps) = ceil(<span id="costT">0</span> × <span id="costFps">0</span>) = <span id="costFrames">0</span>',
    cost_formula_2:
      '2) Vision tokens V = N × k = <span id="costFrames2">0</span> × <span id="costTokPerFrame">258</span> = <span id="costVisionTokens">0</span>',
    cost_formula_3:
      '3) Input tokens In = V + P = <span id="costVisionTokens2">0</span> + <span id="costPromptTokens">0</span> = <span id="costInTokens">0</span>',
    cost_formula_4:
      '4) Billable output Out_bill = Out + Think = <span id="costOutTokens">0</span> + <span id="costThinkTokens">0</span> = <span id="costBillableOutTokens">0</span>',
    cost_formula_5:
      '5) Input cost C_in = In / 1e6 × price_in = <span id="costInTokens2">0</span> / 1e6 × <span id="costPriceIn">0</span> = $<span id="costInUSD">0.0000</span>',
    cost_formula_6:
      '6) Output cost C_out = Out_bill / 1e6 × price_out = <span id="costBillableOutTokens2">0</span> / 1e6 × <span id="costPriceOut">0</span> = $<span id="costOutUSD">0.0000</span>',
    cost_formula_total:
      'Total cost C = C_in + C_out = $<span id="costTotalUSD2">0.0000</span>',
    cost_formula_note:
      'Note: P is fixed prompt/structured output estimate; k is vision token factor per frame; Think is estimated reasoning tokens (priced at output rate).',
    start_detect: 'Start Detection & Labeling',
    prepare_text: 'Preparing...',
    collapse_log: 'Collapse Log',
    expand_log: 'Expand Log',
    detect_preview_alt: 'Live detection preview',
    review_title: 'Results Review',
    review_select_result: 'Select result file...',
    review_select_video: 'Select video file...',
    refresh: 'Refresh',
    review_no_video: 'No video selected',
    review_actions: 'Actions <span class="pill" id="actionCount">0</span>',
    time_range: 'Time Range',
    stat_total_actions: 'Total Actions',
    stat_action_types: 'Action Types',
    stat_avg_duration: 'Avg Duration',
    stat_distribution: 'Action Type Distribution (Bar Chart)',
    process_advice: 'Process Improvement Suggestions',
    no_advice: 'No suggestions',
    overview_title: 'Process Overview',
    station_compare_title: 'Workstation Time Compare',
    deep_dive_title: 'Deep Dive Findings',
    kaizen_title: 'Kaizen Opportunities',
    users_title: 'User Management',
    user_list: 'User List',
    user_actions: 'Actions',
    user_created_at: 'Created At',
    user_data_size: 'Data Size',
    no_users: 'No users',
    calculator_title: 'Cost Calculator',
    calculator_header: 'Token Cost Estimate',
    calculator_model: 'Model',
    calculator_model_default: 'GeniviewK 2.5 - Default',
    calculator_input_tokens: 'Input Tokens',
    calculator_output_tokens: 'Output Tokens',
    calculator_start: 'Calculate',
    calculator_formula_title: 'Formula (GeniviewK 2.5):',
    calculator_price_input: 'Input: ¥0.004 / 1k tokens',
    calculator_price_output: 'Output: ¥0.021 / 1k tokens',
    calculator_input_cost: 'Input Cost',
    calculator_output_cost: 'Output Cost',
    calculator_total_cost: 'Total Cost',
    login_failed: 'Login failed',
    network_error: 'Network error',
    load_failed: 'Load failed',
    load_error: 'Load error: {error}',
    role_admin: 'Admin',
    role_user: 'User',
    status_inactive: 'Inactive',
    status_active: 'Active',
    upload_in_progress: 'Uploading video...',
    not_logged_in_or_expired: 'Not logged in or session expired',
    upload_timeout: 'Network timeout or upload failed (HTTP 0)',
    load_failed_with_error: 'Load failed: {error}',
    edit: 'Edit',
    user_list_load_failed: 'Failed to load users: {error}',
    user_edit: 'Edit User',
    user_new_password_optional: 'New password (leave blank to keep)',
    save_failed: 'Save failed',
    select_video_placeholder: 'Please select a video...',
    expand_or_collapse_log: 'Expand Log',
    select_video_for_duration: 'Select a video to get duration',
    select_file_first: 'Select a file first',
    uploading: 'Uploading...',
    preprocessing_video: 'Preprocessing video...',
    extract_frames_failed: 'Frame extraction failed',
    preprocess_done: 'Preprocessing complete, {count} frames',
    upload_success: 'Upload succeeded!',
    upload_failed: 'Upload failed: {error}',
    upload_error: 'Upload error: {error}',
    select_video_first: 'Select a video first',
    processing_detect: 'Processing (Geniview analysis + visual labeling)...',
    task_start_log: '[{time}] Task started...\nVideo: {video}\nModel: {model}\nFPS: {fps}\n',
    request_params_log: 'Request params: {params}\n',
    start_failed: 'Start failed: {error}',
    detect_progress: 'Detecting: {current} / {total} frames ({pct}%)',
    detect_progress_request: 'Model request progress: {current} / {total} ({pct}%)',
    task_complete: '[{time}] Task completed!\nJSON: {json}\nVideo: {video}\n',
    jump_to_review: 'Jumping to results view...',
    process_failed_check_log: 'Process failed. Check logs.',
    no_matching_result: 'No matching result file for: {name}',
    no_content: '(no content)',
    avg_duration_seconds: 'Average Duration (s)',
    no_advice_data: 'No suggestion data',
    unknown_json_format: 'Unknown JSON format (missing actions). keys: {keys}',
    load_result_failed: 'Failed to load result: {error}',
    unknown_error: 'Unknown error',
    result_not_found: 'Result file not found. Please reselect the video.',
    save_success: 'Saved successfully',
    save_failed_with_error: 'Save failed: {error}',
    load_failed_with_status: 'Load failed: {url} ({status})',
    page_load_failed: 'Page load failed: {error}',
    reason: 'Reason',
    // Phase 2: organization
    nav_org: 'Organization',
    nav_short_org: 'O',
    scope_label: 'Scope',
    scope_loading: 'Loading...',
    scope_all_lines: 'All Lines',
    scope_no_project: 'No Project',
    org_title: 'Organization',
    org_projects: 'Projects',
    org_create_project: 'New Project',
    org_no_projects: 'No projects yet',
    org_project_code: 'Project Code',
    org_project_name: 'Project Name',
    org_project_desc: 'Description',
    org_status: 'Status',
    status_archived: 'Archived',
    org_my_role: 'My Role',
    org_created_at: 'Created At',
    org_actions: 'Actions',
    org_manage_lines: 'Lines',
    org_manage_members: 'Members',
    org_edit: 'Edit',
    org_lines: 'Production Lines',
    org_create_line: 'New Line',
    org_no_lines: 'No lines yet',
    org_line_code: 'Line Code',
    org_line_name: 'Line Name',
    org_process_desc: 'Process Description',
    org_sop: 'Line SOP',
    org_sop_content: 'SOP content (injected for this line, overrides global SOP)',
    org_sop_configured: 'Configured',
    org_sop_empty: 'Not set',
    org_members: 'Members',
    org_member_username: 'Username',
    org_member_username_ph: 'Username',
    org_member_role: 'Project Role',
    org_member_user_role: 'System Role',
    org_no_members: 'No members yet',
    org_add_member: 'Add Member',
    org_remove: 'Remove',
    org_member_removed: 'Member removed',
    role_owner: 'Owner',
    role_editor: 'Editor',
    role_viewer: 'Viewer',
    org_edit_project: 'Edit Project',
    org_edit_line: 'Edit Line',
    org_save_success: 'Saved successfully',
    org_sop_saved: 'SOP saved',
    org_load_failed: 'Load failed',
    org_remove_member_confirm: 'Remove {username} from this project?',
    org_lines_of: 'Lines'
  }
};

let currentLang = 'zh';

function normalizeLang(value) {
  return value === 'en' ? 'en' : 'zh';
}

function getStoredLang() {
  try {
    return normalizeLang(localStorage.getItem('ui_lang') || '');
  } catch {
    return 'zh';
  }
}

function t(key, params) {
  const dict = I18N[currentLang] || I18N.zh;
  let text = dict[key] || I18N.zh[key] || key;
  if (params && typeof text === 'string') {
    Object.keys(params).forEach((k) => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(params[k]));
    });
  }
  return text;
}

function applyLanguage(lang) {
  currentLang = normalizeLang(lang);
  document.documentElement.setAttribute('lang', currentLang === 'en' ? 'en' : 'zh-CN');
  try {
    localStorage.setItem('ui_lang', currentLang);
  } catch {}

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    if (el.id === 'currentVersion' && el.dataset && el.dataset.version) return;
    const key = el.getAttribute('data-i18n');
    if (!key) return;
    el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-html]').forEach((el) => {
    const key = el.getAttribute('data-i18n-html');
    if (!key) return;
    el.innerHTML = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (!key) return;
    el.setAttribute('placeholder', t(key));
  });
  document.querySelectorAll('[data-i18n-alt]').forEach((el) => {
    const key = el.getAttribute('data-i18n-alt');
    if (!key) return;
    el.setAttribute('alt', t(key));
  });
  document.querySelectorAll('[data-i18n-short]').forEach((el) => {
    const key = el.getAttribute('data-i18n-short');
    if (!key) return;
    el.dataset.short = t(key);
  });

  refreshDynamicText();

  const vidSel = document.getElementById('reviewVideoSelect');
  if (vidSel && vidSel.value) {
    const resSel = document.getElementById('reviewResultSelect');
    const oldVal = resSel ? resSel.value : '';
    autoSelectResultByVideoPrefix(vidSel.value);
    const newVal = resSel ? resSel.value : '';
    
    // If selection didn't change (or autoSelect didn't trigger change), force reload
    // to ensure default headers and other UI elements update their language
    if (oldVal === newVal && newVal) {
        resSel.dispatchEvent(new Event('change'));
    }
  }
}

function notify(message) {
  const modal = document.getElementById('notifyModal');
  const title = document.getElementById('notifyTitle');
  const body = document.getElementById('notifyMessage');
  const ok = document.getElementById('btnNotifyOk');
  if (!modal || !body || !ok) return;
  if (title) title.textContent = t('notify_title');
  body.textContent = String(message ?? '');
  modal.classList.add('open');
  ok.onclick = () => {
    modal.classList.remove('open');
  };
  modal.onclick = (e) => {
    if (e.target === modal) modal.classList.remove('open');
  };
  document.addEventListener(
    'keydown',
    (e) => {
      if (e.key !== 'Enter') return;
      ok.click();
    },
    { once: true }
  );
}

function getToken() {
  try {
    return localStorage.getItem('auth_token') || '';
  } catch {
    return '';
  }
}

function setToken(token) {
  try {
    if (token) localStorage.setItem('auth_token', token);
    else localStorage.removeItem('auth_token');
  } catch {}
}

function withMediaToken(url) {
  const token = getToken();
  if (!token) return url;
  const sep = url.includes('?') ? '&' : '?';
  return url + sep + 'token=' + encodeURIComponent(token);
}

function setLoginActive(active) {
  document.body.classList.toggle('login-active', Boolean(active));
  if (active) {
    document.querySelectorAll('.modal').forEach((el) => el.classList.remove('active'));
    document.querySelectorAll('.modal-overlay').forEach((el) => el.classList.remove('open'));
  }
}

function getThemeColor(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback || '';
}

function applyTheme(theme) {
  const normalized = theme === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', normalized);
  try {
    localStorage.setItem('ui_theme', normalized);
  } catch {}
  if (typeof renderStats === 'function') {
    renderStats(currentStats);
  }
}

function bindEnterToButton(container, button) {
  if (!container || !button) return;
  const inputs = container.querySelectorAll('input, select');
  inputs.forEach((el) => {
    el.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      button.click();
    });
  });
}

let currentUser = null;
let userCache = {};

function updateSidebarUserText() {
  const nameEl = document.getElementById('sidebarUser');
  if (!nameEl) return;
  if (!currentUser) {
    nameEl.textContent = t('not_logged_in');
    return;
  }
  nameEl.textContent = `${currentUser.username} (${formatRole(currentUser.role)})`;
}

function updateAdminUI() {
  const navUsers = document.getElementById('navUsers');
  const viewUsers = document.getElementById('view-users');
  const navCalc = document.getElementById('navCalculator');
  const navOrg = document.getElementById('navOrg');
  const viewOrg = document.getElementById('view-org');
  const estimateBtn = document.getElementById('btnEstimateCost');
  const costDiv = document.getElementById('costEstimate');
  const isAdmin = currentUser && currentUser.role === 'admin';
  if (navUsers) navUsers.style.display = isAdmin ? 'block' : 'none';
  if (viewUsers) viewUsers.style.display = isAdmin ? '' : 'none';
  if (navCalc) navCalc.style.display = isAdmin ? 'block' : 'none';
  if (navOrg) navOrg.style.display = isAdmin ? 'block' : 'none';
  if (viewOrg) viewOrg.style.display = isAdmin ? '' : 'none';
  if (estimateBtn) estimateBtn.style.display = 'none';
  if (!isAdmin && costDiv) costDiv.style.display = 'none';
  if (!isAdmin) {
    const view = document.getElementById('view-users');
    const viewCalc = document.getElementById('view-calculator');
    const viewOrg2 = document.getElementById('view-org');
    if (
      (view && view.classList.contains('active')) ||
      (viewCalc && viewCalc.classList.contains('active')) ||
      (viewOrg2 && viewOrg2.classList.contains('active'))
    ) {
      switchTab('review');
    }
  }
}

async function authFetch(url, options = {}) {
  const opts = { ...options };
  opts.headers = { ...(opts.headers || {}) };
  const tokenAtRequest = getToken();
  if (tokenAtRequest) opts.headers['Authorization'] = 'Bearer ' + tokenAtRequest;
  if (!opts.headers['X-UI-Lang']) opts.headers['X-UI-Lang'] = currentLang || 'zh';
  const res = await fetch(url, opts);
  if (res.status === 401) {
    const tokenNow = getToken();
    if (tokenAtRequest && tokenNow && tokenNow === tokenAtRequest) {
      setToken('');
      setLoginActive(true);
    }
  }
  return res;
}

async function refreshMe() {
  const nameEl = document.getElementById('sidebarUser');
  const btnLogin = document.getElementById('btnShowLogin');
  const btnLogout = document.getElementById('btnLogout');
  const token = getToken();
  if (!token) {
    if (btnLogin) btnLogin.style.display = 'inline-block';
    if (btnLogout) btnLogout.style.display = 'none';
    currentUser = null;
    clearScopeUI();
    updateSidebarUserText();
    updateAdminUI();
    setLoginActive(true);
    return;
  }
  try {
    const res = await authFetch('/api/me');
    if (!res.ok) throw new Error('not ok');
    const data = await res.json();
    const user = (data && data.user) || null;
    if (user) {
      currentUser = user;
      updateSidebarUserText();
      if (btnLogin) btnLogin.style.display = 'none';
      if (btnLogout) btnLogout.style.display = 'inline-block';
      updateAdminUI();
      loadScopeProjects();

      const detectModel = document.getElementById('detectModel');
      if (detectModel) {
        const preferredModel = (currentUser.model || 'kimi-2.5').trim();
        const hasOption = Array.from(detectModel.options || []).some((opt) => opt.value === preferredModel);
        if (!hasOption && preferredModel) {
          const dynamicOption = document.createElement('option');
          dynamicOption.value = preferredModel;
          dynamicOption.textContent = preferredModel;
          detectModel.appendChild(dynamicOption);
        }
        detectModel.value = preferredModel || 'kimi-2.5';
      }

      setLoginActive(false);
      return;
    }
  } catch {}
  currentUser = null;
  clearScopeUI();
  updateSidebarUserText();
  if (btnLogin) btnLogin.style.display = 'inline-block';
  if (btnLogout) btnLogout.style.display = 'none';
  updateAdminUI();
  setLoginActive(true);
}

function setupAuthUI() {
  const btnShowLogin = document.getElementById('btnShowLogin');
  const btnConfirm = document.getElementById('btnConfirmLogin');
  const btnLogout = document.getElementById('btnLogout');
  const err = document.getElementById('loginError');
  const loginPage = document.getElementById('loginPage');
  if (btnShowLogin)
    btnShowLogin.onclick = () => {
      if (err) err.textContent = '';
      setLoginActive(true);
    };
  bindEnterToButton(loginPage, btnConfirm);
  if (btnConfirm)
    btnConfirm.onclick = async () => {
      if (err) err.textContent = '';
      const usernameEl = document.getElementById('loginUsername');
      const passwordEl = document.getElementById('loginPassword');
      const u = (usernameEl ? usernameEl.value : '').trim();
      const p = passwordEl ? passwordEl.value : '';
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (!res.ok) {
          if (err)
            err.textContent =
              data && data.error ? `${t('login_failed')}: ${data.error}` : t('login_failed');
          return;
        }
        setToken(data.token);
        await refreshMe();
        await loadVideoList();
        await loadResultList();
      } catch {
        if (err) err.textContent = t('network_error');
      }
    };
  if (btnLogout)
    btnLogout.onclick = async () => {
      try {
        await authFetch('/api/logout', { method: 'POST' });
      } catch {}
      setToken('');
      await refreshMe();
    };
  refreshMe().then(() => pollTaskStatus());
}

function appendLog(container, text) {
  const thumbnailStart = '[THUMBNAIL]';
  const thumbnailEnd = '[THUMBNAIL_END]';

  let processedText = text;
  const startIdx = text.indexOf(thumbnailStart);
  if (startIdx !== -1) {
    const endIdx = text.indexOf(thumbnailEnd, startIdx);
    if (endIdx !== -1) {
      const base64Data = text.substring(startIdx + thumbnailStart.length, endIdx);
      const thumbnailImg = document.getElementById('detectThumbnail');
      const thumbnailContainer = document.getElementById('thumbnailContainer');
      if (thumbnailImg && thumbnailContainer) {
        thumbnailImg.src = 'data:image/jpeg;base64,' + base64Data;
        thumbnailContainer.style.display = 'block';
      }
      processedText = text.substring(0, startIdx) + text.substring(endIdx + thumbnailEnd.length);
    }
  }

  if (processedText) {
    container.appendChild(document.createTextNode(brandReplace(processedText)));
  }
}

function setLog(el, text) {
  if (!el) return;
  el.textContent = brandReplace(text);
}

function isMobile() {
  return window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
}

function setSidebarToggleIcon() {
  const btn = document.getElementById('sidebarToggle');
  if (!btn) return;
  if (isMobile()) {
    btn.textContent = '✕';
    return;
  }
  btn.textContent = document.body.classList.contains('sidebar-collapsed') ? '⟩' : '⟨';
}

function setSidebarCollapsed(nextCollapsed) {
  document.body.classList.toggle('sidebar-collapsed', Boolean(nextCollapsed));
  try {
    localStorage.setItem('sidebar_collapsed', nextCollapsed ? '1' : '0');
  } catch {}
  setSidebarDrawerOpen(false);
  setSidebarToggleIcon();
}

function setSidebarDrawerOpen(nextOpen) {
  document.body.classList.toggle('sidebar-drawer-open', Boolean(nextOpen));
  setSidebarToggleIcon();
}

function initSidebar() {
  let collapsed = false;
  try {
    collapsed = localStorage.getItem('sidebar_collapsed') === '1';
  } catch {}
  if (isMobile()) {
    document.body.classList.remove('sidebar-collapsed');
    setSidebarDrawerOpen(false);
  } else {
    setSidebarCollapsed(collapsed);
    setSidebarDrawerOpen(false);
  }
  setSidebarToggleIcon();

  const btn = document.getElementById('sidebarToggle');
  const overlay = document.getElementById('sidebarOverlay');
  const menuButtons = document.querySelectorAll('[data-menu-button]');
  if (btn) {
    btn.addEventListener('click', () => {
      if (isMobile()) {
        setSidebarDrawerOpen(false);
        return;
      }
      if (document.body.classList.contains('sidebar-collapsed')) {
        setSidebarCollapsed(false);
        return;
      }
      setSidebarCollapsed(true);
    });
  }
  menuButtons.forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = document.body.classList.contains('sidebar-drawer-open');
      if (isOpen) {
        setSidebarDrawerOpen(false);
        return;
      }
      setTimeout(() => setSidebarDrawerOpen(true), 0);
    });
  });
  if (overlay) {
    overlay.addEventListener('click', () => {
      setSidebarDrawerOpen(false);
    });
  }
  window.addEventListener('resize', () => initSidebar());
}

async function fetchVersion() {
  try {
    const res = await fetch('/api/version');
    if (res.ok) {
      const data = await res.json();
      const el = document.getElementById('currentVersion');
      if (el && data.version) {
        el.dataset.version = String(data.version);
        el.textContent = data.version;
      }
    }
  } catch {}
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-item').forEach((el) => el.classList.remove('active'));
  const navTarget = Array.from(document.querySelectorAll('.nav-item')).find(
    (el) => el.dataset.tab === tabId
  );
  if (navTarget) navTarget.classList.add('active');

  document.querySelectorAll('.page-view').forEach((el) => el.classList.remove('active'));
  const view = document.getElementById('view-' + tabId);
  if (view) view.classList.add('active');

  if (tabId === 'detection') loadVideoList();
  if (tabId === 'review') loadResultList();
  if (tabId === 'users') loadUserList();
  if (tabId === 'org') loadOrgData();
  if (tabId === 'settings') fetchVersion();
  setSidebarDrawerOpen(false);
}

function formatBytes(bytes) {
  if (!bytes) return '-';
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) return mb.toFixed(2) + ' MB';
  return (mb / 1024).toFixed(2) + ' GB';
}

function formatRole(role) {
  return role === 'admin' ? t('role_admin') : t('role_user');
}

function formatModel(model) {
  if (!model) return '-';
  const map = {
    'kimi-2.5': 'GeniviewK2.5'
  };
  return map[model] || model;
}

function formatStatus(status) {
  return status === 'inactive' ? t('status_inactive') : t('status_active');
}

function formatTime(value) {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return dt.toLocaleString();
}

function maskApiKey(value) {
  const raw = (value || '').trim();
  if (!raw) return '-';
  const head = raw.slice(0, 8);
  return `${head}******`;
}

function uploadVideoWithProgress(file, barEl, textEl) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload' + scopeQueryString(), true);
    const token = getToken();
    if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.setRequestHeader('X-Filename', encodeURIComponent(file.name));
    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable && barEl) {
        const pct = Math.round((e.loaded / e.total) * 100);
        barEl.style.width = pct + '%';
      }
      if (textEl) textEl.textContent = t('upload_in_progress');
    };
    xhr.onerror = function () {
      reject(new Error(t('network_error')));
    };
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          try {
            const data = JSON.parse(xhr.responseText || '{}');
            if (barEl) barEl.style.width = '100%';
            resolve(data);
          } catch (err) {
            reject(err);
          }
        } else if (xhr.status === 401) {
          setToken('');
          setLoginActive(true);
          reject(new Error(t('not_logged_in_or_expired')));
        } else if (xhr.status === 0) {
          reject(new Error(t('upload_timeout')));
        } else {
          reject(new Error('HTTP ' + xhr.status));
        }
      }
    };
    xhr.send(file);
  });
}

async function loadUserList() {
  if (!currentUser || currentUser.role !== 'admin') return;
  const body = document.getElementById('userTableBody');
  const empty = document.getElementById('userEmpty');
  if (!body || !empty) return;
  body.innerHTML = '';
  empty.style.display = 'none';
  try {
    const res = await authFetch('/api/users');
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data && data.error ? data.error : t('load_failed'));
    }
    const users = data.users || [];
    userCache = {};
    if (!users.length) {
      empty.style.display = 'block';
      return;
    }
    users.forEach((u) => {
      userCache[u.username] = u;
      const tr = document.createElement('tr');
      const statusClass = u.status === 'inactive' ? 'user-pill inactive' : 'user-pill active';
      tr.innerHTML = `
        <td>${u.username}</td>
        <td>${formatRole(u.role)}</td>
        <td>${formatModel(u.model)}</td>
        <td>${u.email || '-'}</td>
        <td>${maskApiKey(u.api_key)}</td>
        <td><span class="${statusClass}">${formatStatus(u.status)}</span></td>
        <td>${formatTime(u.created_at)}</td>
        <td>${formatBytes(u.data_usage)}</td>
        <td>
          <button class="btn btn-small" data-action="edit-user" data-username="${u.username}">${t(
            'edit'
          )}</button>
          <button class="btn btn-small" data-action="view-history" data-username="${u.username}">检测历史</button>
          ${
            u.username !== (currentUser && currentUser.username)
              ? `<button class="btn btn-small btn-danger-outline" data-action="revoke-sessions" data-username="${u.username}" title="${t('revoke_sessions_title')}">${t('revoke_sessions')}</button>`
              : ''
          }
        </td>
      `;
      body.appendChild(tr);
    });
  } catch (e) {
    notify(t('user_list_load_failed', { error: e.message }));
  }
}

async function revokeUserSessions(username) {
  if (!username) return;
  if (!window.confirm(t('revoke_sessions_confirm', { username }))) return;
  try {
    const res = await authFetch('/api/users/revoke_sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'status ' + res.status);
    notify(t('revoke_sessions_done', { username, count: data.revoked ?? 0 }));
  } catch (e) {
    notify(t('revoke_sessions_failed', { error: e.message }));
  }
}

function getBaseName(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  const parts = text.split('/');
  return parts[parts.length - 1] || text;
}

function formatTokenTotal(item) {
  if (!item) return '-';
  const total = Number(item.token_total);
  if (Number.isFinite(total) && total > 0) return String(Math.round(total));
  const parts = [item.token_input, item.token_output, item.token_thinking]
    .map((v) => Number(v))
    .filter((v) => Number.isFinite(v) && v > 0);
  if (!parts.length) return '-';
  return String(Math.round(parts.reduce((a, b) => a + b, 0)));
}

function renderUserHistory(items) {
  const body = document.getElementById('userHistoryBody');
  const empty = document.getElementById('userHistoryEmpty');
  if (!body || !empty) return;
  body.innerHTML = '';
  empty.style.display = 'none';
  if (!items || !items.length) {
    empty.style.display = 'block';
    return;
  }
  items.forEach((item) => {
    const tr = document.createElement('tr');
    const name =
      item.video_name ||
      getBaseName(item.video_path) ||
      getBaseName(item.result_path) ||
      '-';
    const duration = formatSecondsShort(item.video_seconds);
    tr.innerHTML = `
      <td>${formatTime(item.created_at)}</td>
      <td>${name}</td>
      <td>${duration}</td>
      <td>${formatModel(item.model)}</td>
      <td>${formatTokenTotal(item)}</td>
    `;
    body.appendChild(tr);
  });
}

async function openUserHistoryModal(username) {
  const modal = document.getElementById('userHistoryModal');
  const title = document.getElementById('userHistoryTitle');
  const body = document.getElementById('userHistoryBody');
  const empty = document.getElementById('userHistoryEmpty');
  if (!modal || !body || !empty) return;
  if (title) title.textContent = username ? `检测历史 - ${username}` : '检测历史';
  body.innerHTML = `<tr><td colspan="5">加载中...</td></tr>`;
  empty.style.display = 'none';
  modal.classList.add('open');
  try {
    const res = await authFetch(`/api/user_history?username=${encodeURIComponent(username || '')}`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data && data.error ? data.error : t('load_failed'));
    }
    renderUserHistory(data.items || []);
  } catch (e) {
    body.innerHTML = '';
    empty.style.display = 'block';
    notify(t('load_failed') + ': ' + (e.message || ''));
  }
}

function closeUserHistoryModal() {
  const modal = document.getElementById('userHistoryModal');
  if (modal) modal.classList.remove('open');
}

function openUserModal(mode, user) {
  const modal = document.getElementById('userModal');
  const title = document.getElementById('userModalTitle');
  const usernameEl = document.getElementById('userFormUsername');
  const passwordEl = document.getElementById('userFormPassword');
  const passwordLabel = document.getElementById('userFormPasswordLabel');
  const emailEl = document.getElementById('userFormEmail');
  const apiKeyEl = document.getElementById('userFormApiKey');
  const roleEl = document.getElementById('userFormRole');
  const modelEl = document.getElementById('userFormModel');
  const statusEl = document.getElementById('userFormStatus');
  const err = document.getElementById('userFormError');
  if (
    !modal ||
    !title ||
    !usernameEl ||
    !passwordEl ||
    !emailEl ||
    !apiKeyEl ||
    !roleEl ||
    !modelEl ||
    !statusEl ||
    !err
  )
    return;
  err.textContent = '';
  modal.dataset.mode = mode;
  if (mode === 'edit' && user) {
    title.textContent = t('user_edit');
    usernameEl.value = user.username || '';
    usernameEl.readOnly = true;
    passwordEl.value = '';
    if (passwordLabel) passwordLabel.textContent = t('user_new_password_optional');
    emailEl.value = user.email || '';
    apiKeyEl.value = user.api_key || '';
    roleEl.value = user.role || 'user';
    modelEl.value = user.model || 'kimi-2.5';
    statusEl.value = user.status || 'active';
  } else {
    title.textContent = t('user_create');
    usernameEl.value = '';
    usernameEl.readOnly = false;
    passwordEl.value = '';
    if (passwordLabel) passwordLabel.textContent = t('user_password');
    emailEl.value = '';
    apiKeyEl.value = '';
    roleEl.value = 'user';
    modelEl.value = 'kimi-2.5';
    statusEl.value = 'active';
  }
  modal.classList.add('open');
}

function closeUserModal() {
  const modal = document.getElementById('userModal');
  if (modal) modal.classList.remove('open');
}

function setupUserManagement() {
  const btnCreate = document.getElementById('btnCreateUser');
  const btnRefresh = document.getElementById('btnRefreshUsers');
  const btnCancel = document.getElementById('btnUserCancel');
  const btnSave = document.getElementById('btnUserSave');
  const btnHistoryClose = document.getElementById('btnUserHistoryClose');
  const table = document.getElementById('userTable');
  if (btnCreate) btnCreate.onclick = () => openUserModal('create');
  if (btnRefresh) btnRefresh.onclick = () => loadUserList();
  if (btnCancel) btnCancel.onclick = () => closeUserModal();
  if (btnHistoryClose) btnHistoryClose.onclick = () => closeUserHistoryModal();
  if (table) {
    table.addEventListener('click', (e) => {
      const btnEdit = e.target.closest('[data-action="edit-user"]');
      const btnHistory = e.target.closest('[data-action="view-history"]');
      const btnRevoke = e.target.closest('[data-action="revoke-sessions"]');
      if (!btnEdit && !btnHistory && !btnRevoke) return;
      const username = (btnEdit || btnHistory || btnRevoke).getAttribute('data-username');
      if (btnEdit) {
        const user = userCache[username] || null;
        if (user) openUserModal('edit', user);
        return;
      }
      if (btnRevoke) {
        revokeUserSessions(username);
        return;
      }
      openUserHistoryModal(username);
    });
  }
  const modal = document.getElementById('userModal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeUserModal();
    });
  }
  const historyModal = document.getElementById('userHistoryModal');
  if (historyModal) {
    historyModal.addEventListener('click', (e) => {
      if (e.target === historyModal) closeUserHistoryModal();
    });
  }
  bindEnterToButton(modal, btnSave);
  if (btnSave) {
    btnSave.onclick = async () => {
      const modal = document.getElementById('userModal');
      const err = document.getElementById('userFormError');
      const usernameEl = document.getElementById('userFormUsername');
      const passwordEl = document.getElementById('userFormPassword');
      const emailEl = document.getElementById('userFormEmail');
      const apiKeyEl = document.getElementById('userFormApiKey');
      const roleEl = document.getElementById('userFormRole');
      const modelEl = document.getElementById('userFormModel');
      const statusEl = document.getElementById('userFormStatus');
      if (
        !modal ||
        !err ||
        !usernameEl ||
        !passwordEl ||
        !emailEl ||
        !apiKeyEl ||
        !roleEl ||
        !modelEl ||
        !statusEl
      )
        return;
      err.textContent = '';
      const mode = modal.dataset.mode || 'create';
      const username = usernameEl.value.trim();
      const password = passwordEl.value;
      const email = emailEl.value.trim();
      const apiKey = apiKeyEl.value.trim();
      const role = roleEl.value;
      const model = modelEl.value;
      const status = statusEl.value;
      try {
        let res;
        if (mode === 'edit') {
          res = await authFetch('/api/users/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              username,
              email,
              api_key: apiKey,
              role,
              model,
              status,
              new_password: password || ''
            })
          });
        } else {
          res = await authFetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              username,
              password,
              email,
              api_key: apiKey,
              role,
              model,
              status
            })
          });
        }
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data && data.error ? data.error : t('save_failed'));
        }
        closeUserModal();
        await loadUserList();
        await refreshMe();
      } catch (e) {
        err.textContent = e.message || t('save_failed');
      }
    };
  }
}

// =====================================================================
// 阶段 2：作用域（项目/产线）与组织管理
// =====================================================================

let currentScope = { project_id: null, line_id: null };
let scopeProjectsCache = [];

function scopeQueryString() {
  const parts = [];
  if (currentScope.project_id) parts.push('project_id=' + encodeURIComponent(currentScope.project_id));
  if (currentScope.line_id) parts.push('line_id=' + encodeURIComponent(currentScope.line_id));
  return parts.length ? '?' + parts.join('&') : '';
}

function persistScope() {
  try {
    localStorage.setItem('scope_project_id', currentScope.project_id ? String(currentScope.project_id) : '');
    localStorage.setItem('scope_line_id', currentScope.line_id ? String(currentScope.line_id) : '');
  } catch {}
}

function readStoredScope() {
  try {
    return {
      project_id: parseInt(localStorage.getItem('scope_project_id') || '', 10) || null,
      line_id: parseInt(localStorage.getItem('scope_line_id') || '', 10) || null
    };
  } catch {
    return { project_id: null, line_id: null };
  }
}

function clearScopeUI() {
  currentScope = { project_id: null, line_id: null };
  scopeProjectsCache = [];
  const pSel = document.getElementById('scopeProjectSelect');
  const lSel = document.getElementById('scopeLineSelect');
  if (pSel) pSel.innerHTML = `<option value="">${t('scope_no_project')}</option>`;
  if (lSel) lSel.innerHTML = `<option value="">${t('scope_all_lines')}</option>`;
}

async function loadScopeProjects() {
  if (!currentUser) return;
  try {
    const res = await authFetch('/api/projects');
    if (!res.ok) return;
    const data = await res.json();
    scopeProjectsCache = data.projects || [];
    renderScopeProjectSelect();
  } catch (e) {
    console.error(e);
  }
}

function renderScopeProjectSelect() {
  const sel = document.getElementById('scopeProjectSelect');
  if (!sel) return;
  if (!scopeProjectsCache.length) {
    sel.innerHTML = `<option value="">${t('scope_no_project')}</option>`;
    currentScope = { project_id: null, line_id: null };
    renderScopeLineSelect([], null);
    return;
  }
  const stored = readStoredScope();
  sel.innerHTML = '';
  scopeProjectsCache.forEach((p) => {
    const opt = document.createElement('option');
    opt.value = String(p.id);
    opt.textContent = `${p.name} (${p.code})`;
    sel.appendChild(opt);
  });
  const storedOk = scopeProjectsCache.some((p) => String(p.id) === String(stored.project_id));
  sel.value = storedOk ? String(stored.project_id) : String(scopeProjectsCache[0].id);
  currentScope.project_id = parseInt(sel.value, 10) || null;
  loadScopeLines(stored);
}

async function loadScopeLines(stored) {
  const sel = document.getElementById('scopeLineSelect');
  if (!sel || !currentScope.project_id) {
    renderScopeLineSelect([], null);
    return;
  }
  let lines = [];
  try {
    const res = await authFetch('/api/lines?project_id=' + encodeURIComponent(currentScope.project_id));
    if (res.ok) {
      const data = await res.json();
      lines = data.lines || [];
    }
  } catch (e) {
    console.error(e);
  }
  renderScopeLineSelect(lines, stored || readStoredScope());
}

function renderScopeLineSelect(lines, stored) {
  const sel = document.getElementById('scopeLineSelect');
  if (!sel) return;
  sel.innerHTML = `<option value="">${t('scope_all_lines')}</option>`;
  (lines || []).forEach((l) => {
    const opt = document.createElement('option');
    opt.value = String(l.id);
    opt.textContent = `${l.name} (${l.code})`;
    sel.appendChild(opt);
  });
  let lineId = null;
  if (stored && stored.line_id && (lines || []).some((l) => String(l.id) === String(stored.line_id))) {
    sel.value = String(stored.line_id);
    lineId = parseInt(stored.line_id, 10) || null;
  } else {
    sel.value = '';
  }
  currentScope.line_id = lineId;
  persistScope();
  onScopeChanged();
}

function onScopeChanged() {
  // 作用域变化后刷新当前页数据列表
  loadVideoList();
  loadResultList();
}

function setupScopeUI() {
  const pSel = document.getElementById('scopeProjectSelect');
  const lSel = document.getElementById('scopeLineSelect');
  if (pSel) {
    pSel.addEventListener('change', () => {
      currentScope.project_id = parseInt(pSel.value, 10) || null;
      currentScope.line_id = null;
      persistScope();
      loadScopeLines(null);
    });
  }
  if (lSel) {
    lSel.addEventListener('change', () => {
      currentScope.line_id = parseInt(lSel.value, 10) || null;
      persistScope();
      onScopeChanged();
    });
  }
}

// ---------------------------------------------------------------------
// 组织管理页（admin）
// ---------------------------------------------------------------------

let orgProjectsCache = [];
let orgLinesCache = [];
let orgActiveProjectId = null;

function orgStatusBadge(status) {
  const active = String(status || 'active') === 'active';
  return `<span class="org-badge ${active ? 'active' : 'archived'}">${active ? t('status_active') : t('status_archived')}</span>`;
}

function orgRoleText(role) {
  const map = { owner: 'role_owner', editor: 'role_editor', viewer: 'role_viewer' };
  return t(map[String(role || '')] || 'role_editor');
}

async function loadOrgData() {
  if (!currentUser || currentUser.role !== 'admin') return;
  try {
    const res = await authFetch('/api/projects');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    orgProjectsCache = data.projects || [];
    renderOrgProjects();
  } catch (e) {
    console.error(e);
    notify(t('org_load_failed'));
  }
}

function renderOrgProjects() {
  const body = document.getElementById('orgProjectBody');
  const empty = document.getElementById('orgProjectEmpty');
  if (!body) return;
  body.innerHTML = '';
  if (empty) empty.style.display = orgProjectsCache.length ? 'none' : 'block';
  orgProjectsCache.forEach((p) => {
    const tr = document.createElement('tr');
    const desc = String(p.description || '-');
    tr.innerHTML = `
      <td>${p.code || ''}</td>
      <td>${p.name || ''}</td>
      <td title="${desc.replace(/"/g, '&quot;')}">${desc.length > 24 ? desc.slice(0, 24) + '…' : desc}</td>
      <td>${orgStatusBadge(p.status)}</td>
      <td>${orgRoleText(p.my_role)}</td>
      <td>${formatTime(p.created_at)}</td>
      <td>
        <button class="btn btn-small" data-org-lines="${p.id}">${t('org_manage_lines')}</button>
        <button class="btn btn-small" data-org-members="${p.id}">${t('org_manage_members')}</button>
        <button class="btn btn-small" data-org-edit-project="${p.id}">${t('org_edit')}</button>
      </td>`;
    body.appendChild(tr);
  });

  body.querySelectorAll('[data-org-lines]').forEach((btn) => {
    btn.onclick = () => openOrgLines(parseInt(btn.dataset.orgLines, 10));
  });
  body.querySelectorAll('[data-org-members]').forEach((btn) => {
    btn.onclick = () => openMemberModal(parseInt(btn.dataset.orgMembers, 10));
  });
  body.querySelectorAll('[data-org-edit-project]').forEach((btn) => {
    btn.onclick = () => openProjectModal('edit', parseInt(btn.dataset.orgEditProject, 10));
  });

  if (orgActiveProjectId && orgProjectsCache.some((p) => String(p.id) === String(orgActiveProjectId))) {
    loadOrgLines();
  } else {
    const panel = document.getElementById('orgLinesPanel');
    if (panel) panel.style.display = 'none';
    orgActiveProjectId = null;
  }
}

async function loadOrgLines() {
  const panel = document.getElementById('orgLinesPanel');
  const nameEl = document.getElementById('orgLinesProjectName');
  const body = document.getElementById('orgLineBody');
  const empty = document.getElementById('orgLineEmpty');
  if (!panel || !body || !orgActiveProjectId) return;
  const project = orgProjectsCache.find((p) => String(p.id) === String(orgActiveProjectId)) || {};
  if (nameEl) nameEl.textContent = `${project.name || ''} (${project.code || ''})`;
  panel.style.display = 'block';
  try {
    const res = await authFetch('/api/lines?project_id=' + encodeURIComponent(orgActiveProjectId));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    orgLinesCache = data.lines || [];
  } catch (e) {
    console.error(e);
    orgLinesCache = [];
    notify(t('org_load_failed'));
  }
  body.innerHTML = '';
  if (empty) empty.style.display = orgLinesCache.length ? 'none' : 'block';
  orgLinesCache.forEach((l) => {
    const sopSet = String(l.sop_content || '').trim().length > 0;
    const desc = String(l.process_desc || '-');
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${l.code || ''}</td>
      <td>${l.name || ''}</td>
      <td title="${desc.replace(/"/g, '&quot;')}">${desc.length > 24 ? desc.slice(0, 24) + '…' : desc}</td>
      <td>${sopSet ? orgStatusBadge('active').replace(t('status_active'), t('org_sop_configured')) : `<span class="org-badge">${t('org_sop_empty')}</span>`}</td>
      <td>${orgStatusBadge(l.status)}</td>
      <td>${formatTime(l.created_at)}</td>
      <td>
        <button class="btn btn-small" data-org-edit-line="${l.id}">${t('org_edit')}</button>
      </td>`;
    body.appendChild(tr);
  });
  body.querySelectorAll('[data-org-edit-line]').forEach((btn) => {
    btn.onclick = () => openLineModal('edit', parseInt(btn.dataset.orgEditLine, 10));
  });
}

function openOrgLines(projectId) {
  orgActiveProjectId = projectId;
  loadOrgLines();
}

function setupOrgUI() {
  const btnCreate = document.getElementById('btnCreateProject');
  const btnRefresh = document.getElementById('btnRefreshOrg');
  const btnCreateLine = document.getElementById('btnCreateLine');

  if (btnCreate) btnCreate.onclick = () => openProjectModal('create');
  if (btnRefresh) btnRefresh.onclick = () => loadOrgData();
  if (btnCreateLine) {
    btnCreateLine.onclick = () => {
      if (!orgActiveProjectId) {
        notify(t('org_select_project_first'));
        return;
      }
      openLineModal('create');
    };
  }

  // 项目弹窗
  const pModal = document.getElementById('projectModal');
  const btnPCancel = document.getElementById('btnProjectCancel');
  const btnPSave = document.getElementById('btnProjectSave');
  if (btnPCancel) btnPCancel.onclick = () => pModal && pModal.classList.remove('open');
  if (pModal) pModal.onclick = (e) => { if (e.target === pModal) pModal.classList.remove('open'); };
  if (btnPSave) btnPSave.onclick = saveProjectModal;

  // 产线弹窗
  const lModal = document.getElementById('lineModal');
  const btnLCancel = document.getElementById('btnLineCancel');
  const btnLSave = document.getElementById('btnLineSave');
  if (btnLCancel) btnLCancel.onclick = () => lModal && lModal.classList.remove('open');
  if (lModal) lModal.onclick = (e) => { if (e.target === lModal) lModal.classList.remove('open'); };
  if (btnLSave) btnLSave.onclick = saveLineModal;

  // 成员弹窗
  const mModal = document.getElementById('memberModal');
  const btnMClose = document.getElementById('btnMemberClose');
  const btnMAdd = document.getElementById('btnMemberAdd');
  if (btnMClose) btnMClose.onclick = () => mModal && mModal.classList.remove('open');
  if (mModal) mModal.onclick = (e) => { if (e.target === mModal) mModal.classList.remove('open'); };
  if (btnMAdd) btnMAdd.onclick = addMemberFromModal;
}

let projectModalMode = 'create';
let projectModalId = null;

function openProjectModal(mode, projectId) {
  projectModalMode = mode;
  projectModalId = projectId || null;
  const modal = document.getElementById('projectModal');
  const title = document.getElementById('projectModalTitle');
  const code = document.getElementById('projectFormCode');
  const name = document.getElementById('projectFormName');
  const desc = document.getElementById('projectFormDesc');
  const statusGroup = document.getElementById('projectFormStatusGroup');
  const status = document.getElementById('projectFormStatus');
  const err = document.getElementById('projectFormError');
  if (!modal) return;
  if (err) err.textContent = '';
  const project = mode === 'edit' ? orgProjectsCache.find((p) => String(p.id) === String(projectId)) || {} : {};
  if (title) title.textContent = mode === 'edit' ? t('org_edit_project') : t('org_create_project');
  if (code) {
    code.value = project.code || '';
    code.disabled = mode === 'edit';
  }
  if (name) name.value = project.name || '';
  if (desc) desc.value = project.description || '';
  if (statusGroup) statusGroup.style.display = mode === 'edit' ? 'block' : 'none';
  if (status) status.value = String(project.status || 'active');
  modal.classList.add('open');
}

async function saveProjectModal() {
  const err = document.getElementById('projectFormError');
  const code = document.getElementById('projectFormCode');
  const name = document.getElementById('projectFormName');
  const desc = document.getElementById('projectFormDesc');
  const status = document.getElementById('projectFormStatus');
  const modal = document.getElementById('projectModal');
  const showError = (msg) => { if (err) err.textContent = msg; };
  if (err) err.textContent = '';
  if (!name || !String(name.value).trim()) {
    showError(t('org_project_name'));
    return;
  }
  if (projectModalMode === 'create' && (!code || !String(code.value).trim())) {
    showError(t('org_project_code'));
    return;
  }
  try {
    let res;
    if (projectModalMode === 'create') {
      res = await authFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: String(code.value).trim(), name: String(name.value).trim(), description: String(desc.value).trim() })
      });
    } else {
      res = await authFetch('/api/projects/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectModalId,
          name: String(name.value).trim(),
          description: String(desc.value).trim(),
          status: status ? status.value : 'active'
        })
      });
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showError(data.details || data.error || t('save_failed'));
      return;
    }
    if (modal) modal.classList.remove('open');
    notify(t('org_save_success'));
    await loadOrgData();
    await loadScopeProjects();
  } catch (e) {
    showError(e.message || t('save_failed'));
  }
}

let lineModalMode = 'create';
let lineModalId = null;

function openLineModal(mode, lineId) {
  lineModalMode = mode;
  lineModalId = lineId || null;
  const modal = document.getElementById('lineModal');
  const title = document.getElementById('lineModalTitle');
  const code = document.getElementById('lineFormCode');
  const name = document.getElementById('lineFormName');
  const desc = document.getElementById('lineFormProcessDesc');
  const sop = document.getElementById('lineFormSop');
  const statusGroup = document.getElementById('lineFormStatusGroup');
  const status = document.getElementById('lineFormStatus');
  const err = document.getElementById('lineFormError');
  if (!modal) return;
  if (err) err.textContent = '';
  const line = mode === 'edit' ? orgLinesCache.find((l) => String(l.id) === String(lineId)) || {} : {};
  if (title) title.textContent = mode === 'edit' ? t('org_edit_line') : t('org_create_line');
  if (code) {
    code.value = line.code || '';
    code.disabled = mode === 'edit';
  }
  if (name) name.value = line.name || '';
  if (desc) desc.value = line.process_desc || '';
  if (sop) sop.value = line.sop_content || '';
  if (statusGroup) statusGroup.style.display = mode === 'edit' ? 'block' : 'none';
  if (status) status.value = String(line.status || 'active');
  modal.classList.add('open');
}

async function saveLineModal() {
  const err = document.getElementById('lineFormError');
  const code = document.getElementById('lineFormCode');
  const name = document.getElementById('lineFormName');
  const desc = document.getElementById('lineFormProcessDesc');
  const sop = document.getElementById('lineFormSop');
  const status = document.getElementById('lineFormStatus');
  const modal = document.getElementById('lineModal');
  const showError = (msg) => { if (err) err.textContent = msg; };
  if (err) err.textContent = '';
  if (!name || !String(name.value).trim()) {
    showError(t('org_line_name'));
    return;
  }
  if (lineModalMode === 'create' && (!code || !String(code.value).trim())) {
    showError(t('org_line_code'));
    return;
  }
  try {
    let res;
    if (lineModalMode === 'create') {
      res = await authFetch('/api/lines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: orgActiveProjectId,
          code: String(code.value).trim(),
          name: String(name.value).trim(),
          process_desc: String(desc.value).trim(),
          sop_content: sop ? sop.value : ''
        })
      });
    } else {
      res = await authFetch('/api/lines/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          line_id: lineModalId,
          name: String(name.value).trim(),
          process_desc: String(desc.value).trim(),
          sop_content: sop ? sop.value : '',
          status: status ? status.value : 'active'
        })
      });
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showError(data.details || data.error || t('save_failed'));
      return;
    }
    if (modal) modal.classList.remove('open');
    notify(t('org_sop_saved'));
    await loadOrgLines();
    if (currentScope.project_id) loadScopeLines(null);
  } catch (e) {
    showError(e.message || t('save_failed'));
  }
}

let memberModalProjectId = null;

async function openMemberModal(projectId) {
  memberModalProjectId = projectId;
  const modal = document.getElementById('memberModal');
  const title = document.getElementById('memberModalTitle');
  if (!modal) return;
  const project = orgProjectsCache.find((p) => String(p.id) === String(projectId)) || {};
  if (title) title.textContent = `${t('org_members')} · ${project.name || ''}`;
  const input = document.getElementById('memberFormUsername');
  if (input) input.value = '';
  modal.classList.add('open');
  await renderMembers();
}

async function renderMembers() {
  const body = document.getElementById('memberTableBody');
  const empty = document.getElementById('memberEmpty');
  if (!body || !memberModalProjectId) return;
  body.innerHTML = '';
  try {
    const res = await authFetch('/api/members?project_id=' + encodeURIComponent(memberModalProjectId));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const members = data.members || [];
    if (empty) empty.style.display = members.length ? 'none' : 'block';
    members.forEach((m) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${m.username || ''}</td>
        <td>${orgRoleText(m.role)}</td>
        <td>${m.user_role === 'admin' ? t('role_admin') : t('role_user')}</td>
        <td><button class="btn btn-small" data-org-remove-member="${m.username}">${t('org_remove')}</button></td>`;
      body.appendChild(tr);
    });
    body.querySelectorAll('[data-org-remove-member]').forEach((btn) => {
      btn.onclick = async () => {
        if (!confirm(t('org_remove_member_confirm', { username: btn.dataset.orgRemoveMember }))) return;
        try {
          const res2 = await authFetch('/api/members/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: memberModalProjectId, username: btn.dataset.orgRemoveMember })
          });
          if (!res2.ok) {
            const data2 = await res2.json().catch(() => ({}));
            notify(data2.details || data2.error || t('save_failed'));
            return;
          }
          notify(t('org_member_removed'));
          await renderMembers();
          await loadOrgData();
        } catch (e) {
          notify(e.message || t('save_failed'));
        }
      };
    });
  } catch (e) {
    console.error(e);
    notify(t('org_load_failed'));
  }
}

async function addMemberFromModal() {
  const input = document.getElementById('memberFormUsername');
  const roleSel = document.getElementById('memberFormRole');
  if (!input || !String(input.value).trim()) {
    notify(t('org_member_username'));
    return;
  }
  try {
    const res = await authFetch('/api/members', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: memberModalProjectId,
        username: String(input.value).trim(),
        role: roleSel ? roleSel.value : 'editor'
      })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.error || t('save_failed'));
      return;
    }
    notify(t('org_save_success'));
    input.value = '';
    await renderMembers();
  } catch (e) {
    notify(e.message || t('save_failed'));
  }
}

async function loadVideoList() {
  const sel = document.getElementById('detectVideoSelect');
  if (!sel) return;
  try {
    const res = await authFetch('/api/list_videos' + scopeQueryString());
    const data = await res.json();
    sel.innerHTML = `<option value="">${t('select_video_placeholder')}</option>`;
    (data.files || []).forEach((f) => {
      const opt = document.createElement('option');
      opt.value = 'data/' + f;
      opt.textContent = f;
      sel.appendChild(opt);
    });
  } catch (e) {
    sel.innerHTML = `<option>${t('load_failed')}</option>`;
    console.error(e);
  }
}

let detectLogCollapsed = true;
let renderedLogCount = 0;
let isPolling = false;

function updateDetectLogToggleText() {
  const detectLogToggle = document.getElementById('btnToggleDetectLog');
  if (!detectLogToggle) return;
  detectLogToggle.textContent = detectLogCollapsed ? t('expand_log') : t('collapse_log');
}

function refreshDynamicText() {
  updateSidebarUserText();
  updateDetectLogToggleText();

  const videoSel = document.getElementById('reviewVideoSelect');
  const videoName = document.getElementById('videoName');
  if (videoName) {
    if (videoSel && videoSel.value) videoName.textContent = videoSel.value;
    else videoName.textContent = t('review_no_video');
  }

  const actionCount = document.getElementById('actionCount');
  if (actionCount)
    actionCount.textContent = String(
      Number.isFinite(actionCountOverride) ? actionCountOverride : currentActions.length || 0
    );

  const btnUpload = document.getElementById('btnUpload');
  if (btnUpload) btnUpload.textContent = btnUpload.disabled ? t('uploading') : t('upload');

  const uploadInput = document.getElementById('uploadInput');
  const uploadFileName = document.getElementById('uploadFileName');
  if (uploadFileName) {
    if (uploadInput && uploadInput.files && uploadInput.files.length > 0) {
      uploadFileName.textContent = uploadInput.files[0].name;
    } else {
      uploadFileName.textContent = t('file_not_selected');
    }
  }

  const btnStartDetect = document.getElementById('btnStartDetect');
  if (btnStartDetect)
    btnStartDetect.textContent = btnStartDetect.disabled ? t('processing_detect') : t('start_detect');

  const btnMergeKaizen = document.getElementById('btnMergeKaizen');
  if (btnMergeKaizen)
    btnMergeKaizen.textContent = btnMergeKaizen.disabled ? t('merging') : t('merge');
}

function setupDetectionUI() {
  const btnUpload = document.getElementById('btnUpload');
  const btnChooseFile = document.getElementById('btnChooseFile');
  const uploadInput = document.getElementById('uploadInput');
  const uploadFileName = document.getElementById('uploadFileName');
  const modelSelect = document.getElementById('detectModel');
  const fpsInput = document.getElementById('detectFps');
  const costDiv = document.getElementById('costEstimate');
  const btnEstimateCost = document.getElementById('btnEstimateCost');
  const detectVideoSelect = document.getElementById('detectVideoSelect');
  const detectLogPanel = document.getElementById('detectLog');
  const detectLogToggle = document.getElementById('btnToggleDetectLog');

  let selectedVideoDuration = 0;

  const updateDetectLogVisibility = (forceShow = false) => {
    if (!detectLogPanel) return;
    if (forceShow) detectLogCollapsed = false;
    detectLogPanel.style.display = detectLogCollapsed ? 'none' : 'block';
    updateDetectLogToggleText();
  };

  updateDetectLogVisibility();

  if (detectLogToggle) {
    detectLogToggle.addEventListener('click', () => {
      detectLogCollapsed = !detectLogCollapsed;
      updateDetectLogVisibility();
    });
  }

  if (btnChooseFile && uploadInput) {
    btnChooseFile.addEventListener('click', () => {
      uploadInput.click();
    });
  }

  if (uploadInput && uploadFileName) {
    uploadInput.addEventListener('change', () => {
      if (uploadInput.files && uploadInput.files.length > 0) {
        uploadFileName.textContent = uploadInput.files[0].name;
      } else {
        uploadFileName.textContent = t('file_not_selected');
      }
    });
  }

  function updateCost() {
    if (!costDiv) return;
    if (selectedVideoDuration === 0) {
      notify(t('select_video_for_duration'));
      costDiv.style.display = 'none';
      return;
    }

    if (!modelSelect || !fpsInput) return;
    const opt = modelSelect.selectedOptions[0];
    const priceIn = parseFloat(opt.dataset.priceIn);
    const priceOut = parseFloat(opt.dataset.priceOut);

    const fps = parseFloat(fpsInput.value) || 3.0;
    const tokensPerFrame = 258;
    const promptTokens = 800;
    const effectiveDuration = Math.min(selectedVideoDuration, 180);
    const frames = Math.ceil(effectiveDuration * fps);
    const visionTokens = frames * tokensPerFrame;
    const inputTokens = visionTokens + promptTokens;

    const outputTokens = Math.max(
      0,
      parseInt(document.getElementById('estimateOutTokens')?.value || '0', 10) || 0
    );
    const thinkingTokens = Math.max(
      0,
      parseInt(document.getElementById('estimateThinkingTokens')?.value || '0', 10) || 0
    );
    const billableOutputTokens = outputTokens + thinkingTokens;

    const costIn = (inputTokens / 1000000) * priceIn;
    const costOut = (billableOutputTokens / 1000000) * priceOut;
    const totalCost = costIn + costOut;

    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = String(value);
    };

    setText('costValue', totalCost.toFixed(4));
    setText('costDuration', effectiveDuration.toFixed(1));
    setText('costTokensIn', Math.round(inputTokens));
    setText('costTokensOut', Math.round(outputTokens));
    setText('costTokensThink', Math.round(thinkingTokens));

    setText('costT', effectiveDuration.toFixed(3));
    setText('costFps', fps.toFixed(3));
    setText('costFrames', frames);
    setText('costFrames2', frames);
    setText('costTokPerFrame', tokensPerFrame);
    setText('costVisionTokens', visionTokens);
    setText('costVisionTokens2', visionTokens);
    setText('costPromptTokens', promptTokens);
    setText('costInTokens', inputTokens);
    setText('costInTokens2', inputTokens);
    setText('costOutTokens', outputTokens);
    setText('costThinkTokens', thinkingTokens);
    setText('costBillableOutTokens', billableOutputTokens);
    setText('costBillableOutTokens2', billableOutputTokens);
    setText('costPriceIn', priceIn.toFixed(4));
    setText('costPriceOut', priceOut.toFixed(4));
    setText('costInUSD', costIn.toFixed(6));
    setText('costOutUSD', costOut.toFixed(6));
    setText('costTotalUSD2', totalCost.toFixed(6));
    costDiv.style.display = 'block';
  }

  if (btnEstimateCost) btnEstimateCost.addEventListener('click', updateCost);

  if (detectVideoSelect) {
    detectVideoSelect.addEventListener('change', async () => {
      selectedVideoDuration = 0;
      if (costDiv) costDiv.style.display = 'none';

      if (!detectVideoSelect.value) return;

      try {
        const res = await authFetch(
          '/api/video_info?path=' + encodeURIComponent(detectVideoSelect.value)
        );
        if (!res.ok) return;
        const info = await res.json();
        const d = Number(info.duration);
        if (Number.isFinite(d) && d > 0) {
          selectedVideoDuration = d;
        }
      } catch {
        selectedVideoDuration = 0;
      }
    });
  }

  if (btnUpload && uploadInput) {
    btnUpload.addEventListener('click', async () => {
      const file = uploadInput.files[0];
      if (!file) {
        notify(t('select_file_first'));
        return;
      }
      const fps = 3.0;
      const progressWrapper = document.getElementById('uploadProgressWrapper');
      const uploadBar = document.getElementById('uploadVideoProgressBar');
      const uploadText = document.getElementById('uploadVideoProgressText');
      const frameBar = document.getElementById('frameProgressBar');
      const frameText = document.getElementById('frameProgressText');

      if (progressWrapper) {
        progressWrapper.style.display = 'block';
        if (uploadBar) uploadBar.style.width = '0%';
        if (uploadText) uploadText.textContent = t('upload_in_progress');
        if (frameBar) frameBar.style.width = '0%';
        if (frameText) frameText.textContent = '';
      }

      let frameTimer = null;
      let frameProgress = 0;
      btnUpload.disabled = true;
      btnUpload.textContent = t('uploading');

      try {
        const data = await uploadVideoWithProgress(file, uploadBar, uploadText);

        if (data.status === 'success') {
          if (frameText) frameText.textContent = t('preprocessing_video');
          if (frameBar) {
            frameProgress = 0;
            frameBar.style.width = '0%';
            frameTimer = setInterval(() => {
              if (frameProgress < 90) {
                frameProgress += 5;
                frameBar.style.width = frameProgress + '%';
              }
            }, 300);
          }

          const res2 = await authFetch('/api/extract_frames', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_path: data.path, fps })
          });

          let data2;
          try {
            data2 = await res2.json();
          } finally {
            if (frameTimer) {
              clearInterval(frameTimer);
              frameTimer = null;
            }
          }

          if (!res2.ok || data2.status !== 'success') {
            const msg = (data2 && (data2.error || data2.details)) || t('extract_frames_failed');
            throw new Error(msg);
          }

          if (frameBar) {
            frameBar.style.width = '100%';
          }
          if (frameText) {
            const count = typeof data2.frame_count === 'number' ? data2.frame_count : 0;
            frameText.textContent = t('preprocess_done', { count });
          }

          notify(t('upload_success'));
          await loadVideoList();
          const sel = document.getElementById('detectVideoSelect');
          if (sel) {
            sel.value = data.path;
            sel.dispatchEvent(new Event('change'));
          }
        } else {
          notify(t('upload_failed', { error: JSON.stringify(data) }));
        }
      } catch (e) {
        notify(t('upload_error', { error: e.message }));
      } finally {
        btnUpload.disabled = false;
        btnUpload.textContent = t('upload');
        uploadInput.value = '';
        if (uploadFileName) uploadFileName.textContent = t('file_not_selected');
        if (progressWrapper) {
          progressWrapper.style.display = 'none';
        }
        if (uploadBar) {
          uploadBar.style.width = '0%';
        }
        if (uploadText) {
          uploadText.textContent = '';
        }
        if (frameBar) {
          frameBar.style.width = '0%';
        }
        if (frameText) {
          frameText.textContent = '';
        }
      }
    });
  }

  const btnStartDetect = document.getElementById('btnStartDetect');
  if (btnStartDetect) {
    btnStartDetect.addEventListener('click', async () => {
      const videoPath = document.getElementById('detectVideoSelect')?.value;
      const modelSelect = document.getElementById('detectModel');
      let model = modelSelect?.value || '';
      if (!model && currentUser && typeof currentUser.model === 'string') {
        model = currentUser.model.trim();
      }
      if (!model) {
        model = 'kimi-2.5';
      }
      const fpsRaw = parseFloat(document.getElementById('detectFps')?.value);
      const fps = Number.isFinite(fpsRaw) && fpsRaw > 0 ? fpsRaw : 3.0;
      const log = document.getElementById('detectLog');
      const btn = document.getElementById('btnStartDetect');
      const thumbnailContainer = document.getElementById('thumbnailContainer');
      const thumbnailImg = document.getElementById('detectThumbnail');

      if (!videoPath) {
        notify(t('select_video_first'));
        return;
      }

      if (btn) {
        btn.disabled = true;
        btn.textContent = t('processing_detect');
      }
      if (thumbnailContainer) thumbnailContainer.style.display = 'none';
      if (thumbnailImg) thumbnailImg.src = '';

      setLog(
        log,
        t('task_start_log', {
          time: new Date().toLocaleTimeString(),
          video: videoPath,
          model,
          fps
        })
      );
      renderedLogCount = 0;
      if (log) log.scrollTop = log.scrollHeight;

      if (log) {
        appendLog(
          log,
          t('request_params_log', {
            params: JSON.stringify({
              video_path: videoPath,
              model,
              fps,
              ui_lang: currentLang || 'zh',
              project_id: currentScope.project_id || undefined,
              line_id: currentScope.line_id || undefined
            })
          })
        );
        log.scrollTop = log.scrollHeight;
      }

      const taskRunningBar = document.getElementById('taskRunningBar');
      if (taskRunningBar) taskRunningBar.style.display = 'flex';

      try {
        const uiLang = currentLang || 'zh';
        const res = await authFetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-UI-Lang': uiLang },
          body: JSON.stringify({
            video_path: videoPath,
            model,
            fps,
            ui_lang: uiLang,
            project_id: currentScope.project_id || undefined,
            line_id: currentScope.line_id || undefined
          })
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.details || err.error || t('unknown_error'));
        }
        const started = await res.json().catch(() => ({}));
        if (started && typeof started.resolved_model === 'string' && started.resolved_model.trim()) {
          model = started.resolved_model.trim();
        }
        if (log) {
          appendLog(
            log,
            `[INFO] UI Lang: ${uiLang}; Prompt: ${started.prompt_path || 'unknown'}; Resolved Model: ${model}\n`
          );
          log.scrollTop = log.scrollHeight;
        }

        pollTaskStatus();
      } catch (e) {
        if (log) {
          appendLog(log, `[ERROR] ${e.message}\n`);
          log.scrollTop = log.scrollHeight;
        }
        notify(t('start_failed', { error: e.message }));

        if (taskRunningBar) taskRunningBar.style.display = 'none';
        if (btn) {
          btn.disabled = false;
          btn.textContent = t('start_detect');
        }
      }
    });
  }
}

function updateProgressUI(taskData) {
  const pBar = document.getElementById('detectionProgressBar');
  const pText = document.getElementById('detectionProgressText');
  if (taskData.progress && pBar && pText) {
    const { current, total } = taskData.progress;
    if (total > 0) {
      const pct = Math.min(100, Math.max(0, (current / total) * 100)).toFixed(1);
      pBar.style.width = pct + '%';
      const progressKey = taskData.progress_unit === 'request' ? 'detect_progress_request' : 'detect_progress';
      pText.textContent = t(progressKey, { current, total, pct });
    } else {
      pBar.style.width = '0%';
      pText.textContent = t('prepare_text');
    }
  }
}

function applyTaskData(data) {
  const log = document.getElementById('detectLog');
  if (!log || !data.logs) return;

  if (data.logs.length < renderedLogCount) {
    log.textContent = '';
    renderedLogCount = 0;
  }

  if (data.logs.length > renderedLogCount) {
    const fragment = document.createDocumentFragment();
    const newLogs = data.logs.slice(renderedLogCount);

    newLogs.forEach((line) => {
      appendLog(fragment, line);
    });

    log.appendChild(fragment);
    renderedLogCount = data.logs.length;
    log.scrollTop = log.scrollHeight;
  }
}

function handleTaskCompleted(data, log) {
  if (!(data.result && log)) return;

  appendLog(
    log,
    t('task_complete', {
      time: new Date().toLocaleTimeString(),
      json: data.result.json_path,
      video: data.result.video_path
    })
  );
  appendLog(log, t('jump_to_review'));
  log.scrollTop = log.scrollHeight;

  setTimeout(() => {
    switchTab('review');
    loadResultList().then(() => {
      const resultSel = document.getElementById('reviewResultSelect');
      const videoSel = document.getElementById('reviewVideoSelect');
      if (!resultSel || !videoSel) return;
      const targetVideoName = data.result.video_path.split(/[/\\]/).pop();

      // Select video, which triggers autoSelectResultByVideoPrefix (handling language preference)
      Array.from(videoSel.options).forEach((o) => {
        if (o.value.includes(targetVideoName)) videoSel.value = o.value;
      });
      videoSel.dispatchEvent(new Event('change'));
    });
  }, 1500);
}

function handleTaskFailed(data, log) {
  const errorMsg = data.error_msg || t('unknown_error');
  if (log) {
    appendLog(log, `[ERROR] ${errorMsg}\n`);
    log.scrollTop = log.scrollHeight;
  }
  notify(`${t('process_failed_check_log')}\n${t('reason')}: ${errorMsg}`);
}

/**
 * SSE 任务事件流（EventSource 无法携带 Authorization 头，通过 ?token= 鉴权）。
 * onPayload 收到每个状态事件，返回 true 表示终态已处理、流可关闭。
 * 返回 Promise<boolean>：true = SSE 已接管至终态；false = 不可用/中途断开，需回退轮询。
 */
function streamTaskStatus(onPayload) {
  return new Promise((resolve) => {
    if (typeof EventSource === 'undefined') {
      resolve(false);
      return;
    }
    const token = getToken();
    if (!token) {
      resolve(false);
      return;
    }

    let es;
    try {
      es = new EventSource(withMediaToken('/api/task_events'));
    } catch (e) {
      console.warn('EventSource unavailable, fallback to polling:', e);
      resolve(false);
      return;
    }

    let settled = false;
    const finish = (handled) => {
      if (settled) return;
      settled = true;
      try {
        es.close();
      } catch {}
      resolve(handled);
    };

    es.addEventListener('status', (ev) => {
      let payload;
      try {
        payload = JSON.parse(ev.data);
      } catch {
        return;
      }
      let done = false;
      try {
        done = Boolean(onPayload(payload));
      } catch (e) {
        console.error('SSE payload handler error:', e);
      }
      if (done) finish(true);
    });
    es.onerror = () => finish(false); // 连接失败/中断：回退轮询
  });
}

async function pollTaskStatus() {
  if (isPolling) return;

  try {
    const res = await authFetch('/api/task_status');
    if (!res.ok) return;
    const data = await res.json();

    if (data.status === 'none') {
      renderedLogCount = 0;
      return;
    }

    const log = document.getElementById('detectLog');
    const btn = document.getElementById('btnStartDetect');
    const taskRunningBar = document.getElementById('taskRunningBar');

    applyTaskData(data);

    if (data.status !== 'running') {
      return;
    }

    isPolling = true;
    if (btn) {
      btn.disabled = true;
      btn.textContent = t('processing_detect');
    }
    if (taskRunningBar) taskRunningBar.style.display = 'flex';

    updateProgressUI(data);

    // 单个任务数据的统一处理：进度 UI + 增量日志 + 终态分支。返回 true 表示已到终态。
    const consumeTaskData = (taskData) => {
      if (!currentUser) return true;

      updateProgressUI(taskData);
      applyTaskData(taskData);

      if (taskData.status === 'completed') {
        handleTaskCompleted(taskData, log);
        return true;
      }
      if (taskData.status === 'failed') {
        handleTaskFailed(taskData, log);
        return true;
      }
      if (taskData.status === 'none') {
        return true;
      }
      return false;
    };

    // 优先走 SSE 推送；不可用或中途断开时回退 2s 轮询
    const sseHandled = await streamTaskStatus(consumeTaskData);
    if (sseHandled) return;

    while (true) {
      await new Promise((r) => setTimeout(r, 2000));

      if (!currentUser) break;

      const pollRes = await authFetch('/api/task_status');
      if (!pollRes.ok) break;
      const pollData = await pollRes.json();

      if (consumeTaskData(pollData)) break;
    }
  } catch (e) {
    console.error('Polling error:', e);
  } finally {
    isPolling = false;
    const btn = document.getElementById('btnStartDetect');
    const taskRunningBar = document.getElementById('taskRunningBar');
    if (btn) {
      btn.disabled = false;
      btn.textContent = t('start_detect');
    }
    if (taskRunningBar) taskRunningBar.style.display = 'none';
  }
}

let elVideo = null;
let elActions = null;
let elNowPlaying = null;
let elActionCount = null;
let elActiveAction = null;

let currentActions = [];
let currentActionEls = [];
let activeIndex = -1;
let currentJsonPath = '';
let currentActionsHeaders = [];
let actionCountOverride = null;
let currentCycleSelection = null;

let clipStartSec = null;
let clipEndSec = null;
let clipEnforcing = false;
let elTimeline = null;
let elTimelineSegments = null;
let elTimelinePlayhead = null;
let elTimelineHandles = null;
let currentTimelineSegEls = [];
let currentTimelineHandleEls = [];
let isTimelineDragging = false;
let timelinePointerId = null;
let isBoundaryDragging = false;
let boundaryPointerId = null;
let draggingBoundary = null;

let actionDurationColIndex = -1;
let actionTimeColIndex = -1;
let isSavingActions = false;

function formatSecondsShort(sec) {
  const s = Number(sec);
  if (!Number.isFinite(s) || s < 0) return '-';
  const total = Math.floor(s);
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  const pad = (n) => String(n).padStart(2, '0');
  if (hh > 0) return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
  return `${pad(mm)}:${pad(ss)}`;
}

function getClipBounds() {
  if (clipStartSec === null || clipEndSec === null) return null;
  const s = Number(clipStartSec);
  const e = Number(clipEndSec);
  if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return null;
  return { start: s, end: e };
}

function parseTimeFlexible(x) {
  let s = String(x || '').trim();
  if (!s) return NaN;
  s = s.replace(/[()（）]/g, '').trim();
  s = s.replace(/[^\d:.\-]/g, '');
  if (!s) return NaN;
  if (/^\d+(\.\d+)?$/.test(s)) return Number(s);
  const parts = s.split(':').map((p) => p.trim()).filter(Boolean);
  if (parts.length === 2) {
    const aStr = parts[0];
    const bStr = parts[1];
    const a = Number(aStr);
    if (!Number.isFinite(a)) return NaN;
    if (bStr.includes('.')) {
      const b = Number(bStr);
      if (!Number.isFinite(b)) return NaN;
      return a * 60 + b;
    }
    const b = Number(bStr);
    if (!Number.isFinite(b)) return NaN;
    if (a <= 2 && b >= 0 && b <= 59) return a * 60 + b;
    if (b >= 0 && b <= 99) return a + b / 100;
    return a * 60 + b;
  }
  if (parts.length === 3) {
    const h = Number(parts[0]);
    const m = Number(parts[1]);
    const sec = Number(parts[2]);
    if (!Number.isFinite(h) || !Number.isFinite(m) || !Number.isFinite(sec)) return NaN;
    return h * 3600 + m * 60 + sec;
  }
  return NaN;
}

function parseStartEndFromTimeRange(text) {
  const tr = String(text || '').trim();
  if (!tr) return null;
  const normalized = tr.replace(/–|—|~|～|至|to/gi, '-');
  const parts = normalized.split('-').map((x) => x.trim()).filter(Boolean);
  if (parts.length >= 2) {
    const s = parseTimeFlexible(parts[0]);
    const e = parseTimeFlexible(parts[1]);
    if (Number.isFinite(s) && Number.isFinite(e) && e > s) return { s, e };
  }
  const tokens = tr.match(/\d+(?::\d+(?:\.\d+)?)?|\d+\.\d+/g) || [];
  if (tokens.length >= 2) {
    const s = parseTimeFlexible(tokens[0]);
    const e = parseTimeFlexible(tokens[1]);
    if (Number.isFinite(s) && Number.isFinite(e) && e > s) return { s, e };
  }
  return null;
}

function normalizeActionTimeFields(act) {
  if (!act || typeof act !== 'object') return;
  let s = Number.parseFloat(act.start_time);
  let e = Number.parseFloat(act.end_time);
  if (!Number.isFinite(s)) s = parseTimeFlexible(act.start_time);
  if (!Number.isFinite(e)) e = parseTimeFlexible(act.end_time);
  if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
    const pair = parseStartEndFromTimeRange(act.time_range);
    if (pair) {
      s = pair.s;
      e = pair.e;
    }
  }
  if (Number.isFinite(s) && Number.isFinite(e) && e > s) {
    act.start_time = s;
    act.end_time = e;
  }
}

function getActionsTimeRange(actions) {
  const list = Array.isArray(actions) ? actions : [];

  let minStart = Infinity;
  let maxEnd = -Infinity;
  for (const act of list) {
    let s = Number.parseFloat(act?.start_time);
    let e = Number.parseFloat(act?.end_time);
    if (!Number.isFinite(s)) s = parseTimeFlexible(act?.start_time);
    if (!Number.isFinite(e)) e = parseTimeFlexible(act?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      const pair = parseStartEndFromTimeRange(act?.time_range);
      if (pair) {
        s = pair.s;
        e = pair.e;
      }
    }
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) continue;
    minStart = Math.min(minStart, s);
    maxEnd = Math.max(maxEnd, e);
  }
  if (!Number.isFinite(minStart) || !Number.isFinite(maxEnd) || maxEnd <= minStart) return null;
  return { start: Math.max(0, minStart), end: Math.max(0, maxEnd) };
}

function computeCycleSelectionFromTable(headers, rows, actions) {
  const hs = Array.isArray(headers) ? headers : [];
  const rs = Array.isArray(rows) ? rows : [];
  const as = Array.isArray(actions) ? actions : [];
  if (!hs.length || !rs.length || !as.length) return null;

  const cycleColIndex = hs.findIndex((h) => /^(cycle|循环|週期)$/i.test(String(h || '').trim()));
  if (cycleColIndex < 0) return null;

  const seqColIndex = hs.findIndex((h) => /^(序号|编号|No\.?|Index)$/i.test(String(h || '').trim()));
  const normSeq = (v) => String(v ?? '').replace(/\D/g, '');

  const actionIndexBySeq = new Map();
  for (let i = 0; i < as.length; i++) {
    const seq = normSeq(as[i]?.index ?? i + 1);
    if (seq) actionIndexBySeq.set(seq, i);
  }

  const canIndexByRow = rs.length > 0 && rs.length === as.length;
  const byCycle = new Map();

  for (let rowIdx = 0; rowIdx < rs.length; rowIdx++) {
    const cells = Array.isArray(rs[rowIdx]) ? rs[rowIdx] : [];
    let cycleKey = String(cells[cycleColIndex] ?? '').trim();
    if (!cycleKey) cycleKey = '1';

    let actionIdx = -1;
    let seq = '';
    if (canIndexByRow) {
      actionIdx = rowIdx;
    } else {
      const seqCell =
        seqColIndex >= 0 && cells.length > seqColIndex ? cells[seqColIndex] : cells.length ? cells[0] : '';
      seq = normSeq(seqCell);
      const mapped = seq ? actionIndexBySeq.get(seq) : undefined;
      actionIdx = Number.isFinite(mapped) ? mapped : -1;
    }
    if (!Number.isFinite(actionIdx) || actionIdx < 0 || actionIdx >= as.length) continue;

    const act = as[actionIdx];
    if (act && typeof act === 'object') normalizeActionTimeFields(act);
    let s = Number.parseFloat(act?.start_time);
    let e = Number.parseFloat(act?.end_time);
    if (!Number.isFinite(s)) s = parseTimeFlexible(act?.start_time);
    if (!Number.isFinite(e)) e = parseTimeFlexible(act?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) continue;

    let st = byCycle.get(cycleKey);
    if (!st) {
      st = {
        min: Number.POSITIVE_INFINITY,
        max: Number.NEGATIVE_INFINITY,
        actionIdxSet: new Set(),
        seqSet: new Set()
      };
      byCycle.set(cycleKey, st);
    }
    st.min = Math.min(st.min, s);
    st.max = Math.max(st.max, e);
    st.actionIdxSet.add(actionIdx);
    if (!seq) seq = normSeq(act?.index);
    if (seq) st.seqSet.add(seq);
  }

  const durations = [];
  for (const [cycleKey, st] of byCycle.entries()) {
    if (Number.isFinite(st.min) && Number.isFinite(st.max) && st.max > st.min) {
      durations.push({ cycleKey, dur: st.max - st.min, st });
    }
  }
  if (!durations.length) return null;

  const cycleOne = durations.find((x) => normSeq(x.cycleKey) === '1');
  if (cycleOne) {
    return {
      cycleKey: cycleOne.cycleKey,
      range: { start: Math.max(0, cycleOne.st.min), end: Math.max(0, cycleOne.st.max) },
      actionIdxSet: cycleOne.st.actionIdxSet,
      seqSet: cycleOne.st.seqSet
    };
  }

  const mean = durations.reduce((sum, x) => sum + x.dur, 0) / durations.length;
  durations.sort((a, b) => {
    const da = Math.abs(a.dur - mean);
    const db = Math.abs(b.dur - mean);
    if (da !== db) return da - db;
    if (a.dur !== b.dur) return a.dur - b.dur;
    return String(a.cycleKey).localeCompare(String(b.cycleKey));
  });

  const best = durations[0];
  return {
    cycleKey: best.cycleKey,
    range: { start: Math.max(0, best.st.min), end: Math.max(0, best.st.max) },
    actionIdxSet: best.st.actionIdxSet,
    seqSet: best.st.seqSet
  };
}

function setClipRange(startSec, endSec, { seek = true } = {}) {
  const s = Number(startSec);
  const e = Number(endSec);
  if (!Number.isFinite(s) || !Number.isFinite(e)) return false;
  if (e <= s) return false;
  clipStartSec = Math.max(0, s);
  clipEndSec = Math.max(0, e);
  updateTimelinePlayhead();
  if (seek && window.seekVideo) window.seekVideo(clipStartSec, { play: false });
  return true;
}

function clearClipRange() {
  clipStartSec = null;
  clipEndSec = null;
  updateTimelinePlayhead();
}

function updateActionComputedFields(act) {
  if (!act || typeof act !== 'object') return;
  const s = Number.parseFloat(act.start_time);
  const e = Number.parseFloat(act.end_time);
  if (!Number.isFinite(s) || !Number.isFinite(e)) return;
  const d = Math.max(0, e - s);
  act.duration = d.toFixed(1);
  act.time_range = `${s.toFixed(2)} - ${e.toFixed(2)}`;
}

function updateActionRowTimeCells(index) {
  if (!Number.isFinite(index)) return;
  const row = currentActionEls[index];
  if (!row) return;
  const act = currentActions[index];
  if (!act) return;

  const children = row.children ? Array.from(row.children) : [];
  if (actionDurationColIndex >= 0 && children[actionDurationColIndex]) {
    const v = act.duration || '';
    children[actionDurationColIndex].textContent = v;
    children[actionDurationColIndex].title = v;
  }
  if (actionTimeColIndex >= 0 && children[actionTimeColIndex]) {
    const v = act.time_range || '';
    children[actionTimeColIndex].textContent = v;
    children[actionTimeColIndex].title = v;
  }
}

async function persistActionsUpdate({ silentSuccess = false } = {}) {
  if (isSavingActions) return;
  const resultFile = currentJsonPath || document.getElementById('reviewResultSelect')?.value;
  if (!resultFile) {
    notify(t('result_not_found'));
    return;
  }

  isSavingActions = true;
  try {
    const res = await authFetch('/api/update_result', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ json_path: resultFile, actions: currentActions })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || t('unknown_error'));
    }
    const payload = await res.json().catch(() => ({}));
    const parsed = payload && payload.data ? payload.data : null;
    if (parsed && typeof parsed === 'object') {
      if (Array.isArray(parsed.actions)) currentActions = parsed.actions;
      if (parsed.actions_table && parsed.actions_table.headers && parsed.actions_table.rows) {
        renderActionsTable(parsed.actions_table, currentActions);
      } else {
        renderActions(currentActions);
      }
      refreshStationCompareChart();
      // 阶段 3：编辑可能改变动作区间，刷新缩略图（签名变化时后端自动重建）
      fetchResultThumbs(resultFile);
      renderVaNvaStats(currentActions);
      if (!silentSuccess) notify(t('save_success'));
      return;
    }
    refreshStationCompareChart();
    fetchResultThumbs(resultFile);
    renderVaNvaStats(currentActions);
    if (!silentSuccess) notify(t('save_success'));
  } catch (e) {
    notify(t('save_failed_with_error', { error: e.message }));
    console.error(e);
  } finally {
    isSavingActions = false;
  }
}

function clampToClip(t) {
  const x = Number(t);
  if (!Number.isFinite(x)) return x;
  if (clipStartSec === null || clipEndSec === null) return x;
  return Math.min(Number(clipEndSec), Math.max(Number(clipStartSec), x));
}

function enforceClipRange() {
  if (!elVideo) return;
  if (clipStartSec === null || clipEndSec === null) return;
  if (!Number.isFinite(clipStartSec) || !Number.isFinite(clipEndSec)) return;
  if (clipEnforcing) return;
  const s = Number(clipStartSec);
  const e = Number(clipEndSec);
  const t = Number(elVideo.currentTime);
  if (!Number.isFinite(t)) return;
  clipEnforcing = true;
  try {
    if (t < s) {
      elVideo.currentTime = s;
      return;
    }
    if (t > e) {
      try {
        elVideo.pause();
      } catch {}
      elVideo.currentTime = e;
    }
  } finally {
    clipEnforcing = false;
  }
}

function updateTimelinePlayhead() {
  if (!elTimelinePlayhead) return;
  if (!elVideo) {
    elTimelinePlayhead.style.left = '0%';
    return;
  }

  const bounds = getClipBounds();
  if (!bounds) {
    elTimelinePlayhead.style.left = '0%';
    return;
  }

  const t = clampToClip(elVideo.currentTime);
  const denom = bounds.end - bounds.start;
  if (!(denom > 0)) {
    elTimelinePlayhead.style.left = '0%';
    return;
  }

  const pct = ((t - bounds.start) / denom) * 100;
  elTimelinePlayhead.style.left = Math.max(0, Math.min(100, pct)) + '%';
}

function hashStringToHue(input) {
  const s = String(input || '');
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0;
  }
  return h % 360;
}

function colorForAction(action, idx) {
  const base = (action && (action.label || action.therblig || action.value_added)) || '';
  const baseTrimmed = String(base || '').trim();
  const n = Number.isFinite(Number(idx)) ? Number(idx) : 0;
  const hue = baseTrimmed ? (hashStringToHue(`${baseTrimmed}#${n}`) + n * 47) % 360 : (n * 137.508) % 360;
  return `hsl(${hue}, 70%, 55%)`;
}

function updateTimelineActive(index) {
  for (let i = 0; i < currentTimelineSegEls.length; i++) {
    const el = currentTimelineSegEls[i];
    if (!el) continue;
    if (i === index) el.classList.add('active');
    else el.classList.remove('active');
  }
}

function renderActionTimeline(actions) {
  if (!elTimelineSegments) return;
  if (elTimeline && !elTimelineHandles) {
    elTimelineHandles = document.getElementById('actionTimelineHandles');
    if (!elTimelineHandles) {
      elTimelineHandles = document.createElement('div');
      elTimelineHandles.id = 'actionTimelineHandles';
      elTimelineHandles.className = 'action-timeline-handles';
      if (elTimelinePlayhead && elTimelinePlayhead.parentNode === elTimeline) {
        elTimeline.insertBefore(elTimelineHandles, elTimelinePlayhead);
      } else {
        elTimeline.appendChild(elTimelineHandles);
      }
    }
  }

  const list = Array.isArray(actions) ? actions : [];
  currentTimelineSegEls = [];
  currentTimelineHandleEls = [];
  elTimelineSegments.innerHTML = '';
  if (elTimelineHandles) elTimelineHandles.innerHTML = '';

  const range =
    currentCycleSelection &&
    currentCycleSelection.range &&
    Number.isFinite(currentCycleSelection.range.start) &&
    Number.isFinite(currentCycleSelection.range.end) &&
    currentCycleSelection.range.end > currentCycleSelection.range.start
      ? currentCycleSelection.range
      : getActionsTimeRange(list);
  if (!range) {
    clearClipRange();
    updateTimelinePlayhead();
    return;
  }

  const shouldSeek =
    !elVideo ||
    clipStartSec === null ||
    clipEndSec === null ||
    !Number.isFinite(elVideo.currentTime) ||
    elVideo.currentTime < range.start ||
    elVideo.currentTime > range.end;
  setClipRange(range.start, range.end, { seek: shouldSeek });

  const denom = range.end - range.start;
  if (!(denom > 0)) {
    updateTimelinePlayhead();
    return;
  }

  for (let idx = 0; idx < list.length; idx++) {
    const allow =
      currentCycleSelection && currentCycleSelection.actionIdxSet instanceof Set
        ? currentCycleSelection.actionIdxSet
        : null;
    if (allow && !allow.has(idx)) {
      currentTimelineSegEls.push(null);
      continue;
    }
    const act = list[idx];
    const s = Number.parseFloat(act?.start_time);
    const e = Number.parseFloat(act?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      currentTimelineSegEls.push(null);
      continue;
    }

    const leftPct = ((Math.max(range.start, s) - range.start) / denom) * 100;
    const widthPct = ((Math.min(range.end, e) - Math.max(range.start, s)) / denom) * 100;
    if (!(widthPct > 0)) {
      currentTimelineSegEls.push(null);
      continue;
    }

    const seg = document.createElement('div');
    seg.className = 'action-timeline-segment';
    seg.dataset.index = String(idx);
    seg.style.left = leftPct + '%';
    seg.style.width = widthPct + '%';
    const segColor = colorForAction(act, idx);
    seg.style.background = segColor;
    seg.style.backgroundColor = segColor;
    const label = act?.label ? String(act.label) : '';
    seg.title = `${idx + 1} ${label} ${formatSecondsShort(s)} - ${formatSecondsShort(e)}`;
    elTimelineSegments.appendChild(seg);
    currentTimelineSegEls.push(seg);
  }

  if (elTimelineHandles) {
    const allow =
      currentCycleSelection && currentCycleSelection.actionIdxSet instanceof Set
        ? currentCycleSelection.actionIdxSet
        : null;
    const idxs = allow
      ? Array.from(allow)
          .map((x) => Number(x))
          .filter((x) => Number.isFinite(x) && x >= 0 && x < list.length)
          .sort((a, b) => a - b)
      : null;
    if (idxs && idxs.length >= 2) {
      for (let k = 0; k < idxs.length - 1; k++) {
        const leftIdx = idxs[k];
        const rightIdx = idxs[k + 1];
        const a = list[leftIdx];
        const b = list[rightIdx];
        const s1 = Number.parseFloat(a?.start_time);
        const e1 = Number.parseFloat(a?.end_time);
        const s2 = Number.parseFloat(b?.start_time);
        const e2 = Number.parseFloat(b?.end_time);
        if (!Number.isFinite(s1) || !Number.isFinite(e1) || !Number.isFinite(s2) || !Number.isFinite(e2)) continue;
        if (!(e1 > s1) || !(e2 > s2)) continue;
        const boundary = Number.isFinite(e1) ? e1 : s2;
        if (!Number.isFinite(boundary) || boundary <= range.start || boundary >= range.end) continue;

        const leftPct = ((boundary - range.start) / denom) * 100;
        const h = document.createElement('div');
        h.className = 'action-timeline-handle';
        h.dataset.leftIndex = String(leftIdx);
        h.dataset.rightIndex = String(rightIdx);
        h.style.left = leftPct + '%';
        h.title = `${leftIdx + 1} / ${rightIdx + 1} ${formatSecondsShort(boundary)}`;
        elTimelineHandles.appendChild(h);
        currentTimelineHandleEls.push(h);
      }
    } else {
      for (let i = 0; i < list.length - 1; i++) {
        const a = list[i];
        const b = list[i + 1];
        const s1 = Number.parseFloat(a?.start_time);
        const e1 = Number.parseFloat(a?.end_time);
        const s2 = Number.parseFloat(b?.start_time);
        const e2 = Number.parseFloat(b?.end_time);
        if (!Number.isFinite(s1) || !Number.isFinite(e1) || !Number.isFinite(s2) || !Number.isFinite(e2)) continue;
        if (!(e1 > s1) || !(e2 > s2)) continue;
        const boundary = Number.isFinite(e1) ? e1 : s2;
        if (!Number.isFinite(boundary) || boundary <= range.start || boundary >= range.end) continue;

        const leftPct = ((boundary - range.start) / denom) * 100;
        const h = document.createElement('div');
        h.className = 'action-timeline-handle';
        h.dataset.leftIndex = String(i);
        h.dataset.rightIndex = String(i + 1);
        h.style.left = leftPct + '%';
        h.title = `${i + 1} / ${i + 2} ${formatSecondsShort(boundary)}`;
        elTimelineHandles.appendChild(h);
        currentTimelineHandleEls.push(h);
      }
    }
  }

  updateTimelineActive(activeIndex);
  updateTimelinePlayhead();
}

function seekFromTimelineClientX(clientX, { play } = {}) {
  if (!elTimeline || !elVideo || !window.seekVideo) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const rect = elTimeline.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
  const pct = rect.width > 0 ? x / rect.width : 0;
  const t = bounds.start + pct * (bounds.end - bounds.start);
  const shouldPlay = typeof play === 'boolean' ? play : !elVideo.paused;
  window.seekVideo(t, { play: shouldPlay });
}

function updateTimelineSegmentStyle(idx) {
  const seg = currentTimelineSegEls[idx];
  if (!seg) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const denom = bounds.end - bounds.start;
  if (!(denom > 0)) return;

  const act = currentActions[idx];
  const s = Number.parseFloat(act?.start_time);
  const e = Number.parseFloat(act?.end_time);
  if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return;

  const leftPct = ((Math.max(bounds.start, s) - bounds.start) / denom) * 100;
  const widthPct = ((Math.min(bounds.end, e) - Math.max(bounds.start, s)) / denom) * 100;
  seg.style.left = leftPct + '%';
  seg.style.width = Math.max(0, widthPct) + '%';
  const segColor = colorForAction(act, idx);
  seg.style.background = segColor;
  seg.style.backgroundColor = segColor;
  const label = act?.label ? String(act.label) : '';
  seg.title = `${idx + 1} ${label} ${formatSecondsShort(s)} - ${formatSecondsShort(e)}`;
}

function updateTimelineHandleStyle(handleEl, boundaryTime) {
  if (!handleEl) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const denom = bounds.end - bounds.start;
  if (!(denom > 0)) return;
  const pct = ((boundaryTime - bounds.start) / denom) * 100;
  handleEl.style.left = Math.max(0, Math.min(100, pct)) + '%';
  handleEl.title = `${Number(handleEl.dataset.leftIndex || 0) + 1} / ${
    Number(handleEl.dataset.rightIndex || 1) + 1
  } ${formatSecondsShort(boundaryTime)}`;
}

function setBoundaryTime(leftIdx, rightIdx, boundaryTime) {
  const a = currentActions[leftIdx];
  const b = currentActions[rightIdx];
  if (!a || !b) return;

  a.end_time = boundaryTime;
  b.start_time = boundaryTime;
  updateActionComputedFields(a);
  updateActionComputedFields(b);
  updateActionRowTimeCells(leftIdx);
  updateActionRowTimeCells(rightIdx);
  updateTimelineSegmentStyle(leftIdx);
  updateTimelineSegmentStyle(rightIdx);
  updateTimelinePlayhead();
}

function adjustBoundaryFromClientX(clientX) {
  if (!draggingBoundary || !elTimeline) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const rect = elTimeline.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
  const pct = rect.width > 0 ? x / rect.width : 0;
  const raw = bounds.start + pct * (bounds.end - bounds.start);

  const leftIdx = draggingBoundary.leftIdx;
  const rightIdx = draggingBoundary.rightIdx;
  const a = currentActions[leftIdx];
  const b = currentActions[rightIdx];
  if (!a || !b) return;

  const aStart = Number.parseFloat(a.start_time);
  const bEnd = Number.parseFloat(b.end_time);
  if (!Number.isFinite(aStart) || !Number.isFinite(bEnd)) return;

  const minGap = 0.1;
  const minT = Math.max(bounds.start, aStart + minGap);
  const maxT = Math.min(bounds.end, bEnd - minGap);
  if (!(maxT > minT)) return;
  const t = Math.max(minT, Math.min(maxT, raw));

  setBoundaryTime(leftIdx, rightIdx, t);
  updateTimelineHandleStyle(draggingBoundary.el, t);
}

async function loadResultList() {
  const resSel = document.getElementById('reviewResultSelect');
  const vidSel = document.getElementById('reviewVideoSelect');
  if (!resSel || !vidSel) return;
  try {
    const res = await authFetch('/api/list_results' + scopeQueryString());
    const data = await res.json();

    const oldRes = resSel.value;
    const oldVid = vidSel.value;

    resSel.innerHTML = `<option value="">${t('review_select_result')}</option>`;
    vidSel.innerHTML = `<option value="">${t('review_select_video')}</option>`;

    (data.files || []).forEach((f) => {
      const opt = document.createElement('option');
      opt.value = 'result/' + f;
      opt.textContent = f;
      if (f.endsWith('.json') || f.endsWith('.md')) resSel.appendChild(opt);
      else if (f.endsWith('.mp4')) vidSel.appendChild(opt.cloneNode(true));
    });

    if (oldRes) {
      resSel.value = oldRes;
      currentJsonPath = oldRes;
    }
    if (oldVid) vidSel.value = oldVid;
  } catch (e) {
    console.error(e);
  }
}

function autoSelectResultByVideoPrefix(videoPath) {
  const resSel = document.getElementById('reviewResultSelect');
  if (!resSel) return;
  if (!videoPath) return;

  const videoFile = String(videoPath).split('/').pop() || '';
  const videoBase = videoFile.replace(/\.[^.]+$/, '');
  if (!videoBase) return;

  const targetPrefix = currentLang === 'en' ? 'en_' + videoBase : videoBase;

  let best = null;
  let bestScore = -1;
  let bestLen = -1;

  for (const opt of Array.from(resSel.options)) {
    const val = opt.value || '';
    if (!val || (!val.endsWith('.json') && !val.endsWith('.md'))) continue;
    const resFile = String(val).split('/').pop() || '';
    const resBase = resFile.replace(/\.[^.]+$/, '');
    if (!resBase) continue;

    let score = 0;

    // 1. Language match
    if (resBase === targetPrefix) score += 100;
    else if (resBase.startsWith(targetPrefix)) score += 50;

    // 2. Fallback match (Original logic components)
    if (resBase === videoBase) score += 20;
    else if (resBase.startsWith(videoBase)) score += 10;
    else if (videoBase.startsWith(resBase)) score += 5;

    // 3. File type preference
    if (val.endsWith('.md')) score += 2;

    if (score > 0) {
      if (score > bestScore) {
        bestScore = score;
        best = opt;
        bestLen = resBase.length;
      } else if (score === bestScore) {
        if (resBase.length > bestLen) {
          best = opt;
          bestLen = resBase.length;
        }
      }
    }
  }

  if (!best) {
    resSel.value = '';
    currentJsonPath = '';
    notify(t('no_matching_result', { name: videoFile }));
    return;
  }

  if (resSel.value !== best.value) {
    resSel.value = best.value;
    currentJsonPath = best.value;
    resSel.dispatchEvent(new Event('change'));
  }
}

function renderMdView(data) {
  const md = document.getElementById('mdResultView');
  const legacy = document.getElementById('legacyStatsView');
  if (md) md.style.display = 'flex';
  if (legacy) legacy.style.display = 'none';

  if (md) md.style.display = 'grid';

  const escapeHtml = (s) =>
    String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const safeLink = (href) => {
    const u = String(href || '').trim();
    if (!u) return '';
    const lower = u.toLowerCase();
    if (lower.startsWith('javascript:') || lower.startsWith('data:')) return '';
    return u;
  };

  const mdToHtml = (input) => {
    const text = String(input || '');
    const lines = text.replace(/\r\n/g, '\n').split('\n');
    let out = '';
    let inCode = false;
    let codeBuf = [];
    let inUl = false;
    let inOl = false;
    let inBlockquote = false;
    const flushLists = () => {
      if (inUl) {
        out += '</ul>';
        inUl = false;
      }
      if (inOl) {
        out += '</ol>';
        inOl = false;
      }
    };
    const closeBlockquote = () => {
      if (inBlockquote) {
        out += '</blockquote>';
        inBlockquote = false;
      }
    };
    const inline = (s) => {
      let x = escapeHtml(s);
      x = x.replace(/`([^`]+)`/g, (_m, c) => `<code>${escapeHtml(c)}</code>`);
      x = x.replace(/\*\*([^*]+)\*\*/g, (_m, c) => `<strong>${escapeHtml(c)}</strong>`);
      x = x.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, txt, href) => {
        const safe = safeLink(href);
        if (!safe) return escapeHtml(txt);
        return `<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          txt
        )}</a>`;
      });
      return x;
    };

    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      const line = raw.replace(/\t/g, '  ');

      if (line.trim().startsWith('```')) {
        if (!inCode) {
          flushLists();
          closeBlockquote();
          inCode = true;
          codeBuf = [];
        } else {
          const code = codeBuf.join('\n');
          out += `<pre><code>${escapeHtml(code)}</code></pre>`;
          inCode = false;
          codeBuf = [];
        }
        continue;
      }

      if (inCode) {
        codeBuf.push(raw);
        continue;
      }

      const trimmed = line.trim();
      if (!trimmed) {
        flushLists();
        closeBlockquote();
        continue;
      }

      if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        flushLists();
        closeBlockquote();
        out += '<hr />';
        continue;
      }

      const bq = trimmed.startsWith('>') ? trimmed.replace(/^>\s?/, '') : null;
      if (bq !== null) {
        flushLists();
        if (!inBlockquote) {
          out += '<blockquote>';
          inBlockquote = true;
        }
        out += `<p>${inline(bq)}</p>`;
        continue;
      }
      closeBlockquote();

      const h = trimmed.match(/^(#{1,3})\s+(.*)$/);
      if (h) {
        flushLists();
        const level = h[1].length;
        out += `<h${level}>${inline(h[2])}</h${level}>`;
        continue;
      }

      const ol = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (ol) {
        if (inUl) {
          out += '</ul>';
          inUl = false;
        }
        if (!inOl) {
          out += '<ol>';
          inOl = true;
        }
        out += `<li>${inline(ol[2])}</li>`;
        continue;
      }

      const ul = trimmed.match(/^[-*]\s+(.*)$/);
      if (ul) {
        if (inOl) {
          out += '</ol>';
          inOl = false;
        }
        if (!inUl) {
          out += '<ul>';
          inUl = true;
        }
        out += `<li>${inline(ul[1])}</li>`;
        continue;
      }

      flushLists();
      out += `<p>${inline(trimmed)}</p>`;
    }

    if (inCode) {
      out += `<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`;
    }
    flushLists();
    closeBlockquote();
    return out || `<p>${escapeHtml(t('no_content'))}</p>`;
  };

  const setMd = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = mdToHtml(value || t('no_content'));
  };
  setMd('mdOverview', data.overview || '');
  setMd('mdDeepDive', data.deep_dive || '');
  setMd('mdKaizen', data.kaizen || '');
}

const STATION_COMPARE_MAX = 12;
const stationCompareCache = new Map();
const stationCompareVisibleByPath = new Map();
let stationCompareLastItems = [];
let stationCompareRenderSeq = 0;

function _stationLabelFromPath(resultPath) {
  const file = String(resultPath || '').split('/').pop() || '';
  const base = file.replace(/\.[^.]+$/, '');
  const cleaned = base.replace(/_\d{2}\.\d{2}\.\d{2}\.\d{2}$/, '');
  return cleaned || base || file || String(resultPath || '');
}

function _hashColor(key) {
  const s = String(key || 'unknown');
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return `hsl(${hue} 65% 55%)`;
}

function _isStationCompareVisible(path) {
  const key = String(path || '');
  if (!key) return true;
  const v = stationCompareVisibleByPath.get(key);
  return v !== false;
}

function _renderStationCompareControls(items) {
  const root = document.getElementById('stationCompareControls');
  if (!root) return;
  root.innerHTML = '';

  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  if (list.length === 0) {
    root.style.display = 'none';
    return;
  }
  root.style.display = 'flex';

  for (const item of list) {
    const label = document.createElement('label');
    label.className = 'station-compare-toggle';
    label.title = item.label || '';

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = _isStationCompareVisible(item.path);
    input.addEventListener('change', () => {
      stationCompareVisibleByPath.set(String(item.path || ''), Boolean(input.checked));
      const filtered = (stationCompareLastItems || []).filter((x) => _isStationCompareVisible(x?.path));
      _renderStationCompareChart(filtered);
    });

    const span = document.createElement('span');
    span.textContent = item.label || '';

    label.appendChild(input);
    label.appendChild(span);
    root.appendChild(label);
  }
}

function _normalizeActionsForCompare(actions) {
  const out = [];
  for (const raw of actions || []) {
    if (raw && typeof raw === 'object') normalizeActionTimeFields(raw);
    let s = Number.parseFloat(raw?.start_time);
    let e = Number.parseFloat(raw?.end_time);
    if (!Number.isFinite(s)) s = parseTimeFlexible(raw?.start_time);
    if (!Number.isFinite(e)) e = parseTimeFlexible(raw?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      const pair = parseStartEndFromTimeRange(raw?.time_range);
      if (pair) {
        s = pair.s;
        e = pair.e;
      }
    }
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) continue;
    out.push({
      index: String(raw?.index ?? ''),
      label: String(raw?.label ?? ''),
      start: s,
      end: e
    });
  }
  out.sort((a, b) => a.start - b.start);
  return out;
}

function _extractActionsFromResultDetails(data) {
  if (data && typeof data === 'object') {
    const isMd = data.overview !== undefined || data.deep_dive !== undefined || data.kaizen !== undefined;
    if (isMd) return Array.isArray(data.actions) ? data.actions : [];
    if (Array.isArray(data.actions)) return data.actions;
    if (data.model_output && Array.isArray(data.model_output.actions)) return data.model_output.actions;
    if (data.output && Array.isArray(data.output.actions)) return data.output.actions;
  }
  if (Array.isArray(data)) return data;
  return [];
}

async function _fetchStationCompareItem(resultPath) {
  const key = String(resultPath || '');
  if (!key) return null;
  if (stationCompareCache.has(key)) return stationCompareCache.get(key);
  const apiUrl = '/api/result_details?path=' + encodeURIComponent(key) + '&ts=' + Date.now();
  const res = await authFetch(apiUrl);
  if (!res.ok) return null;
  const data = await res.json().catch(() => null);
  const actionsRaw = _extractActionsFromResultDetails(data);
  const table =
    data &&
    typeof data === 'object' &&
    data.actions_table &&
    Array.isArray(data.actions_table.headers) &&
    Array.isArray(data.actions_table.rows)
      ? data.actions_table
      : null;
  const sel = table ? computeCycleSelectionFromTable(table.headers, table.rows, actionsRaw) : null;
  const normSeq = (v) => String(v ?? '').replace(/\D/g, '');
  const actionsFiltered =
    sel && (sel.actionIdxSet instanceof Set || sel.seqSet instanceof Set)
      ? actionsRaw.filter((a, i) => {
          if (sel.actionIdxSet instanceof Set && sel.actionIdxSet.has(i)) return true;
          if (sel.seqSet instanceof Set) {
            const s = normSeq(a?.index);
            return s ? sel.seqSet.has(s) : false;
          }
          return false;
        })
      : actionsRaw;
  const actions = _normalizeActionsForCompare(actionsFiltered);
  const item = { path: key, label: _stationLabelFromPath(key), actions };
  stationCompareCache.set(key, item);
  return item;
}

function _renderStationCompareChart(items) {
  const root = document.getElementById('stationCompareChart');
  if (!root) return;

  const chartHeight = 420;
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  const valid = list.filter((x) => Array.isArray(x.actions) && x.actions.length > 0);
  if (valid.length === 0) {
    root.innerHTML = `<div style="color: var(--muted); font-size: 13px;">${t('no_content')}</div>`;
    return;
  }

  const ranges = valid.map((x) => {
    const minS = x.actions.reduce((m, a) => Math.min(m, a.start), Number.POSITIVE_INFINITY);
    const maxE = x.actions.reduce((m, a) => Math.max(m, a.end), 0);
    return Math.max(0, maxE - minS);
  });
  const globalMax = Math.max(0.1, ...ranges);

  const axis = document.createElement('div');
  axis.className = 'station-compare-axis';
  axis.style.height = `${chartHeight}px`;

  for (let i = 0; i <= 4; i++) {
    const pct = i / 4;
    const tSec = globalMax * pct;

    const tick = document.createElement('div');
    tick.className = 'station-compare-axis-tick';
    tick.style.bottom = `${pct * 100}%`;
    tick.textContent = `${tSec.toFixed(1)}s`;
    axis.appendChild(tick);

    const line = document.createElement('div');
    line.className = 'station-compare-axis-line';
    line.style.bottom = `${pct * 100}%`;
    axis.appendChild(line);
  }

  const bars = document.createElement('div');
  bars.className = 'station-compare-bars';
  bars.style.height = `${chartHeight}px`;

  for (const item of valid.slice(0, STATION_COMPARE_MAX)) {
    const station = document.createElement('div');
    station.className = 'station-compare-station';

    const bar = document.createElement('div');
    bar.className = 'station-compare-bar';
    bar.style.height = `${chartHeight}px`;

    const acts = item.actions;
    const minS = acts.reduce((m, a) => Math.min(m, a.start), Number.POSITIVE_INFINITY);
    const maxE = acts.reduce((m, a) => Math.max(m, a.end), 0);
    const total = Math.max(0, maxE - minS);

    const segments = [];
    let cursor = 0;
    for (const a of acts) {
      const s = Math.max(0, a.start - minS);
      const e = Math.max(s, a.end - minS);
      if (s > cursor) segments.push({ kind: 'gap', start: cursor, end: s });
      segments.push({ kind: 'act', start: s, end: e, label: a.label, index: a.index });
      cursor = Math.max(cursor, e);
    }
    if (globalMax > cursor) segments.push({ kind: 'gap', start: cursor, end: globalMax });

    const heights = [];
    let sum = 0;
    for (const seg of segments) {
      const d = Math.max(0, seg.end - seg.start);
      let h = Math.round((d / globalMax) * chartHeight);
      if (seg.kind === 'act' && d > 0 && h < 1) h = 1;
      heights.push(h);
      sum += h;
    }

    if (sum > chartHeight) {
      let excess = sum - chartHeight;
      for (let i = 0; i < segments.length && excess > 0; i++) {
        const minH = segments[i].kind === 'act' ? 1 : 0;
        const reducible = Math.max(0, heights[i] - minH);
        const take = Math.min(reducible, excess);
        heights[i] -= take;
        excess -= take;
      }
    } else if (sum < chartHeight && heights.length) {
      heights[heights.length - 1] += chartHeight - sum;
    }

    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const d = Math.max(0, seg.end - seg.start);
      const h = heights[i];
      if (h <= 0) continue;
      const el = document.createElement('div');
      el.className = 'station-compare-seg' + (seg.kind === 'gap' ? ' gap' : '');
      el.style.height = `${h}px`;
      if (seg.kind === 'act') {
        const key = String(seg.label || seg.index || '');
        el.style.background = _hashColor(key);
        el.title = `${seg.index ? seg.index + ' ' : ''}${seg.label || ''}\n${seg.start.toFixed(
          2
        )}s - ${seg.end.toFixed(2)}s (${d.toFixed(2)}s)`;
      }
      bar.appendChild(el);
    }

    const label = document.createElement('div');
    label.className = 'station-compare-label';
    label.title = item.label;
    label.textContent = item.label;

    station.appendChild(bar);
    station.appendChild(label);
    bars.appendChild(station);
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'station-compare';
  wrapper.appendChild(axis);
  wrapper.appendChild(bars);

  root.innerHTML = '';
  root.appendChild(wrapper);
}

async function refreshStationCompareChart() {
  const root = document.getElementById('stationCompareChart');
  if (!root) return;
  const resSel = document.getElementById('reviewResultSelect');
  if (!resSel) return;

  const seq = ++stationCompareRenderSeq;
  const elControls = document.getElementById('stationCompareControls');
  const pathsMd = Array.from(resSel.options)
    .map((o) => o.value || '')
    .filter((v) => v && v.endsWith('.md'));
  const pathsJson = Array.from(resSel.options)
    .map((o) => o.value || '')
    .filter((v) => v && v.endsWith('.json'));

  const paths = (currentLang === 'en' ? pathsMd.filter((v) => v.split('/').pop().startsWith('en_')) : pathsMd.filter((v) => !v.split('/').pop().startsWith('en_'))).slice(0, STATION_COMPARE_MAX);
  if (paths.length === 0) {
    // Fallback to all MD or all JSON if no language-specific MD files found
    const allPaths = (pathsMd.length ? pathsMd : pathsJson).slice(0, STATION_COMPARE_MAX);
    paths.push(...allPaths);
  }

  for (const p of paths) {
    const key = String(p || '');
    if (key && !stationCompareVisibleByPath.has(key)) stationCompareVisibleByPath.set(key, true);
  }

  const currentPath = currentJsonPath || resSel.value;
  if (currentPath && Array.isArray(currentActions) && currentActions.length) {
    const actionsAll = _normalizeActionsForCompare(currentActions);
    const r =
      currentCycleSelection &&
      currentCycleSelection.range &&
      Number.isFinite(currentCycleSelection.range.start) &&
      Number.isFinite(currentCycleSelection.range.end) &&
      currentCycleSelection.range.end > currentCycleSelection.range.start
        ? currentCycleSelection.range
        : null;
    const actions = r ? actionsAll.filter((a) => a.start >= r.start && a.end <= r.end) : actionsAll;
    stationCompareCache.set(String(currentPath), {
      path: String(currentPath),
      label: _stationLabelFromPath(currentPath),
      actions
    });
  }

  root.innerHTML = `<div style="color: var(--muted); font-size: 13px;">${t('loading')}</div>`;
  if (elControls) elControls.innerHTML = '';
  const items = [];
  for (const p of paths) {
    try {
      const item = await _fetchStationCompareItem(p);
      if (item) items.push(item);
    } catch {}
    if (seq !== stationCompareRenderSeq) return;
  }

  if (seq !== stationCompareRenderSeq) return;
  stationCompareLastItems = items;
  _renderStationCompareControls(items);
  const filtered = items.filter((x) => _isStationCompareVisible(x?.path));
  _renderStationCompareChart(filtered);
}

function renderLegacyView() {
  const md = document.getElementById('mdResultView');
  const legacy = document.getElementById('legacyStatsView');
  if (md) md.style.display = 'none';
  if (legacy) legacy.style.display = 'none';
}

function getDefaultActionsHeaders() {
  return [
    t('action_index'),
    t('action_desc'),
    t('therblig_type'),
    t('is_process'),
    t('is_move'),
    t('is_check'),
    t('is_wait'),
    t('estimated_duration'),
    t('value_added'),
    t('hands'),
    t('time_range'),
    t('variation_source')
  ];
}

function renderDefaultActionsHeader() {
  const elHeader = document.getElementById('actionsListHeader');
  if (!elHeader) return;
  elHeader.innerHTML = '';
  
  const headers = getDefaultActionsHeaders();
  if (headers.length !== 12) {
      elHeader.style.gridTemplateColumns = `repeat(${headers.length}, minmax(100px, 1fr))`;
  } else {
      elHeader.style.removeProperty('grid-template-columns');
  }

  headers.forEach(h => {
    const div = document.createElement('div');
    div.textContent = h;
    elHeader.appendChild(div);
  });
}

function renderActionsTable(table, actions) {
  const elHeader = document.getElementById('actionsListHeader');
  const elList = document.getElementById('actionsList');
  if (!elHeader || !elList) return;

  elHeader.innerHTML = '';
  elList.innerHTML = '';

  currentActions = Array.isArray(actions) ? actions : [];
  currentActionEls = new Array(currentActions.length).fill(null);
  activeIndex = -1;
  actionCountOverride = null;
  currentActions.forEach(normalizeActionTimeFields);

  const normSeq = (v) => String(v ?? '').replace(/\D/g, '');
  const actionIndexBySeq = new Map();
  for (let i = 0; i < currentActions.length; i++) {
    const seq = normSeq(currentActions[i]?.index ?? i + 1);
    if (seq) actionIndexBySeq.set(seq, i);
  }

  const rawHeaders =
    table && Array.isArray(table.headers) && table.headers.length > 0
      ? table.headers
      : getDefaultActionsHeaders();
  const headersRaw = Array.isArray(rawHeaders) ? [...rawHeaders] : [...getDefaultActionsHeaders()];
  const rowsRaw = table && Array.isArray(table.rows) ? table.rows : [];
  const canIndexByRow = Array.isArray(rowsRaw) && rowsRaw.length > 0 && rowsRaw.length === currentActions.length;

  const cycleColIndexRaw = headersRaw.findIndex((h) => /^(cycle|循环|週期)$/i.test(String(h || '').trim()));
  const seqColIndexRaw = headersRaw.findIndex((h) => /^(序号|编号|No\.?|Index)$/i.test(String(h || '').trim()));
  currentCycleSelection = computeCycleSelectionFromTable(headersRaw, rowsRaw, currentActions);
  let selectedCycle = currentCycleSelection ? String(currentCycleSelection.cycleKey || '') : '';
  if (cycleColIndexRaw >= 0 && Array.isArray(rowsRaw) && rowsRaw.length) {
    const hasNonNumericCycle = rowsRaw.some((row) => {
      const cells = Array.isArray(row) ? row : [];
      const rawCycle = String(cells[cycleColIndexRaw] ?? '').trim();
      return rawCycle && !normSeq(rawCycle);
    });
    if (hasNonNumericCycle) selectedCycle = '';
  }

  let headers = headersRaw;
  const rows = rowsRaw;
  if (cycleColIndexRaw >= 0) {
    headers = headersRaw.filter((_h, i) => i !== cycleColIndexRaw);
  }
  currentActionsHeaders = headers;
    
  actionDurationColIndex = headers.findIndex((h) => /耗时|duration/i.test(String(h || '')));
  actionTimeColIndex =
    headers.findIndex((h) => /(时间区间|时间段|time\s*range)/i.test(String(h || ''))) >= 0
      ? headers.findIndex((h) => /(时间区间|时间段|time\s*range)/i.test(String(h || '')))
      : headers.findIndex((h) => /时间|time/i.test(String(h || '')));
  const seqColIndex = headers.findIndex((h) => /^(序号|编号|No\.?|Index)$/i.test(String(h || '').trim()));
  
  // Calculate max columns from data to ensure we display everything
  let maxCols = headers.length;
  const rowsForDisplay =
    cycleColIndexRaw >= 0 && Array.isArray(rows) ? rows.map((r) => (Array.isArray(r) ? r.filter((_c, i) => i !== cycleColIndexRaw) : [])) : rows;
  rowsForDisplay.forEach((r) => {
      if (Array.isArray(r) && r.length > maxCols) maxCols = r.length;
  });
  
  // Extend headers if needed
  if (maxCols > headers.length) {
      const diff = maxCols - headers.length;
      for (let i = 0; i < diff; i++) {
          headers.push(`Col ${headers.length + 1}`);
      }
  }

  let gridTemplate;
  const buildFixedGridTemplate = (headersList, colCount) => {
    const n = Math.max(0, Number(colCount) || 0);
    if (!n) return '';
    const smallCol = '56px';
    const cols = [];
    for (let i = 0; i < n; i++) {
      const h = String((headersList && headersList[i]) || '').trim();
      if (/^(cycle|循环|週期)$/i.test(h)) {
        cols.push(smallCol);
        continue;
      }
      if (/^(序号|编号|No\.?|Index)$/i.test(h)) {
        cols.push(smallCol);
        continue;
      }
      if (/(动作描述|motion description|description)/i.test(h)) {
        cols.push('320px');
        continue;
      }
      if (/(动素|therblig)/i.test(h)) {
        cols.push('200px');
        continue;
      }
      if (/(耗时|duration|time\s*\(s\)|est\.\s*duration)/i.test(h)) {
        cols.push('120px');
        continue;
      }
      if (/(时间区间|时间段|time\s*range)/i.test(h)) {
        cols.push('180px');
        continue;
      }
      if (/(增值|VA\/NVA|value)/i.test(h)) {
        cols.push('120px');
        continue;
      }
      if (/(左右手|hand)/i.test(h)) {
        cols.push('90px');
        continue;
      }
      if (/(波动来源|variation)/i.test(h)) {
        cols.push('160px');
        continue;
      }
      if (/^(是否加工|process|是否搬运|transport|是否检查|inspect|是否等待|wait|是否存储|store)$/i.test(h)) {
        cols.push('90px');
        continue;
      }
      cols.push('140px');
    }
    return cols.join(' ');
  };

  gridTemplate = buildFixedGridTemplate(headers, maxCols);

  // 阶段 3：首列为动作首帧缩略图列
  gridTemplate = '64px ' + gridTemplate;
  headers.unshift(t('action_thumb'));
  maxCols += 1;
  
  elHeader.style.display = 'grid';
  elHeader.style.gridTemplateColumns = gridTemplate;
  elHeader.style.width = 'max-content';
  elHeader.style.minWidth = 'max-content';

  headers.forEach(h => {
    const div = document.createElement('div');
    div.textContent = h;
    div.title = h;
    div.style.padding = '8px';
    div.style.fontWeight = 'bold';
    div.style.borderRight = '1px solid var(--border)';
    elHeader.appendChild(div);
  });
  
  let renderedCount = 0;
  rowsForDisplay.forEach((cellsDisplay, idx) => {
    const cellsRaw = Array.isArray(rows) && Array.isArray(rows[idx]) ? rows[idx] : [];
    const rowDiv = document.createElement('div');
    rowDiv.className = 'action-item';
    rowDiv.dataset.index = String(idx);
    let actionIdx = -1;
    let cycleKey = '';
    if (cycleColIndexRaw >= 0) {
      cycleKey = String((cellsRaw && cellsRaw.length ? cellsRaw[cycleColIndexRaw] : '') ?? '').trim();
      if (!cycleKey) cycleKey = '1';
    }
    if (canIndexByRow && idx < currentActions.length) {
      actionIdx = idx;
    } else {
      const seqCell =
        seqColIndexRaw >= 0 && cellsRaw && cellsRaw.length > seqColIndexRaw
          ? cellsRaw[seqColIndexRaw]
          : cellsRaw && cellsRaw.length
          ? cellsRaw[0]
          : '';
      const seq = normSeq(seqCell);
      const mapped = seq ? actionIndexBySeq.get(seq) : undefined;
      actionIdx = Number.isFinite(mapped) ? mapped : idx;
    }
    if (!Number.isFinite(actionIdx) || actionIdx < 0 || actionIdx >= currentActions.length) actionIdx = -1;
    rowDiv.dataset.actionIndex = String(actionIdx);
    rowDiv.style.display = 'grid';
    rowDiv.style.gridTemplateColumns = gridTemplate;
    rowDiv.style.width = 'max-content';
    
    const action = actionIdx >= 0 ? currentActions[actionIdx] : null;
    if (action && cycleKey) action.cycle = cycleKey;
    if (action) currentActionEls[actionIdx] = rowDiv;
    if (selectedCycle && cycleColIndexRaw >= 0 && normSeq(cycleKey) !== normSeq(selectedCycle)) return;
    rowDiv.onclick = () => {
      if (actionIdx >= 0) {
        const act = currentActions[actionIdx];
        if (act) {
          normalizeActionTimeFields(act);
          const t = Number.parseFloat(act.start_time);
          if (window.seekVideo && Number.isFinite(t)) window.seekVideo(t, { play: true });
        }
      }
      document.querySelectorAll('.action-item').forEach((el) => el.classList.remove('active'));
      rowDiv.classList.add('active');
    };
    
    // Ensure we render all cells, even if they exceed original header count
    // Pad with empty strings if row is shorter than maxCols
    const renderCells = Array.isArray(cellsDisplay) ? [...cellsDisplay] : [];
    while (renderCells.length < maxCols - 1) {
        renderCells.push('');
    }
    // 阶段 3：首格为缩略图占位（由 applyThumbsToRows 异步填充）
    renderCells.unshift('');

    renderCells.forEach((cellText, cellIdx) => {
      const cellDiv = document.createElement('div');
      cellDiv.className = 'col-content';
      if (cellIdx === 0) {
        cellDiv.className = 'col-content action-thumb-cell';
        cellDiv.dataset.actionIndex = String(actionIdx);
      } else {
        cellDiv.textContent = cellText;
        cellDiv.title = cellText;
      }
      cellDiv.style.padding = '8px';
      cellDiv.style.borderRight = '1px solid var(--border)';
      cellDiv.style.overflow = 'hidden';
      cellDiv.style.textOverflow = 'ellipsis';
      rowDiv.appendChild(cellDiv);
    });

    elList.appendChild(rowDiv);
    currentActionEls.push(rowDiv);
    renderedCount += 1;
  });

  elList.style.width = 'max-content';
  elList.style.minWidth = 'max-content';
  
  // Ensure container scrolls
  const panelBody = document.querySelector('.actions-panel-body');
  if (panelBody) {
      panelBody.style.overflowX = 'auto';
      panelBody.style.maxWidth = '100%';
      panelBody.style.display = 'block'; 
  }

  if (selectedCycle) actionCountOverride = renderedCount;
  renderActionTimeline(currentActions);
  enforceClipRange();
  refreshDynamicText();
  applyThumbsToRows();
}

function renderActions(actions) {
   if (!actions) return;
   const rows = actions.map(act => {
       return [
           act.index || '',
           act.label || '',
           act.therblig || '',
           act.is_process || '',
           act.is_move || '',
           act.is_check || '',
           act.is_wait || '',
           act.duration || '',
           act.value_added || '',
           act.hands || '',
           act.time_range || '',
           act.variation || ''
       ];
   });
   renderActionsTable({ headers: getDefaultActionsHeaders(), rows: rows }, actions);
}

// ---------------------------------------------------------------------------
// 阶段 3：动作首帧缩略图
// ---------------------------------------------------------------------------

let currentThumbs = [];
let currentThumbsPath = '';

async function fetchResultThumbs(path) {
  if (!path) return;
  currentThumbsPath = path;
  try {
    const res = await authFetch('/api/result_thumbs?path=' + encodeURIComponent(path));
    if (!res.ok) throw new Error('status ' + res.status);
    const data = await res.json();
    if (path !== currentThumbsPath) return;
    currentThumbs = Array.isArray(data.thumbs) ? data.thumbs : [];
  } catch (e) {
    console.warn('thumbs unavailable:', e);
    currentThumbs = [];
  }
  applyThumbsToRows();
}

function buildThumbPlaceholder() {
  const ph = document.createElement('div');
  ph.className = 'action-thumb action-thumb-placeholder';
  ph.textContent = '—';
  return ph;
}

function applyThumbsToRows() {
  document.querySelectorAll('#actionsList .action-item').forEach((row) => {
    const cell = row.querySelector('.action-thumb-cell');
    if (!cell) return;
    const idx = Number(cell.dataset.actionIndex);
    cell.innerHTML = '';
    if (Number.isFinite(idx) && currentThumbs[idx]) {
      const img = document.createElement('img');
      img.className = 'action-thumb';
      img.loading = 'lazy';
      img.alt = '';
      img.src = withMediaToken('/' + currentThumbs[idx]);
      img.onerror = () => {
        if (img.parentNode) img.replaceWith(buildThumbPlaceholder());
      };
      cell.appendChild(img);
    } else {
      cell.appendChild(buildThumbPlaceholder());
    }
  });
}

// ---------------------------------------------------------------------------
// 阶段 3：VA / NVA 增值统计
// ---------------------------------------------------------------------------

const VANVA_COLORS = {
  va: '#4caf50',
  nva: '#ef5350',
  nnva: '#ffa726',
  unknown: '#90a4ae'
};

let vanvaChartInstance = null;

function classifyVaNva(value) {
  const v = String(value ?? '').trim().toLowerCase();
  if (!v) return 'unknown';
  if (v.includes('必要') || v.includes('nnva') || v.includes('necessary')) return 'nnva';
  if (v.includes('非增值') || v === 'nva' || v.includes('non-value') || v.includes('non value')) return 'nva';
  if (v.includes('增值') || v === 'va' || v.includes('value-added') || v.includes('value added')) return 'va';
  return 'unknown';
}

function renderVaNvaStats(actions) {
  const panel = document.getElementById('vanvaPanel');
  if (!panel) return;
  const list = Array.isArray(actions) ? actions : [];

  const buckets = { va: 0, nva: 0, nnva: 0, unknown: 0 };
  const counts = { va: 0, nva: 0, nnva: 0, unknown: 0 };
  let total = 0;
  for (const act of list) {
    const s = Number.parseFloat(act?.start_time);
    const e = Number.parseFloat(act?.end_time);
    const dur = Number.isFinite(s) && Number.isFinite(e) ? Math.max(0, e - s) : 0;
    const key = classifyVaNva(act?.value_added);
    buckets[key] += dur;
    counts[key] += 1;
    total += dur;
  }

  if (!total) {
    panel.style.display = 'none';
    if (vanvaChartInstance) {
      try { vanvaChartInstance.destroy(); } catch {}
      vanvaChartInstance = null;
    }
    return;
  }

  panel.style.display = 'block';
  const keys = ['va', 'nva', 'nnva', 'unknown'];
  const labels = {
    va: t('vanva_va'),
    nva: t('vanva_nva'),
    nnva: t('vanva_nnva'),
    unknown: t('vanva_unknown')
  };

  const canvas = document.getElementById('vanvaChart');
  if (canvas && typeof Chart !== 'undefined') {
    const ctx = canvas.getContext('2d');
    if (vanvaChartInstance) {
      try { vanvaChartInstance.destroy(); } catch {}
      vanvaChartInstance = null;
    }
    vanvaChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: keys.map((k) => labels[k]),
        datasets: [
          {
            data: keys.map((k) => Number(buckets[k].toFixed(2))),
            backgroundColor: keys.map((k) => VANVA_COLORS[k]),
            borderColor: 'rgba(0,0,0,0.12)',
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        cutout: '58%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => {
                const k = keys[item.dataIndex];
                const pct = total > 0 ? ((buckets[k] / total) * 100).toFixed(1) : '0';
                return `${item.label}: ${buckets[k].toFixed(1)}s (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }

  const legend = document.getElementById('vanvaLegend');
  if (legend) {
    legend.innerHTML = '';
    keys.forEach((k) => {
      const pct = total > 0 ? ((buckets[k] / total) * 100).toFixed(1) : '0';
      const rowEl = document.createElement('div');
      rowEl.className = 'vanva-legend-row';
      rowEl.innerHTML = `
        <span class="vanva-legend-dot" style="background:${VANVA_COLORS[k]}"></span>
        <span class="vanva-legend-name">${labels[k]}</span>
        <span class="vanva-legend-meta">${counts[k]} ${t('vanva_actions_unit')} · ${buckets[k].toFixed(1)}s · ${pct}%</span>
      `;
      legend.appendChild(rowEl);
    });
    const totalRow = document.createElement('div');
    totalRow.className = 'vanva-legend-row vanva-legend-total';
    totalRow.innerHTML = `
      <span class="vanva-legend-dot" style="background:transparent"></span>
      <span class="vanva-legend-name">${t('vanva_total')}</span>
      <span class="vanva-legend-meta">${total.toFixed(1)}s</span>
    `;
    legend.appendChild(totalRow);
  }
}

// ---------------------------------------------------------------------------
// 阶段 3：动作表 CSV 导出（所见即所得）
// ---------------------------------------------------------------------------

function exportActionsCsv() {
  const headerEl = document.getElementById('actionsListHeader');
  const listEl = document.getElementById('actionsList');
  if (!headerEl || !listEl || !currentActions.length) {
    notify(t('no_result_selected'));
    return;
  }

  const headers = Array.from(headerEl.querySelectorAll('div'))
    .map((el) => el.textContent || '')
    .slice(1); // 跳过缩略图列
  const rows = Array.from(listEl.querySelectorAll('.action-item')).map((row) =>
    Array.from(row.querySelectorAll('.col-content'))
      .filter((el) => !el.classList.contains('action-thumb-cell'))
      .map((el) => el.textContent || '')
  );

  const esc = (v) => {
    const s = String(v ?? '');
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [headers.map(esc).join(',')];
  rows.forEach((r) => lines.push(r.map(esc).join(',')));
  const csv = '\uFEFF' + lines.join('\r\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const base = (currentJsonPath || 'actions')
    .split('/')
    .pop()
    .replace(/\.[^.]+$/, '');
  a.href = url;
  a.download = `${base}_actions.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// 阶段 3：修订历史（留痕 + 回滚）
// ---------------------------------------------------------------------------

async function showRevisionHistory() {
  if (!currentJsonPath) {
    notify(t('no_result_selected'));
    return;
  }
  const modal = document.getElementById('revisionModal');
  const listEl = document.getElementById('revisionList');
  if (!modal || !listEl) return;
  modal.classList.add('open');
  listEl.innerHTML = `<div style="color:var(--muted)">loading...</div>`;
  try {
    const res = await authFetch('/api/result_revisions?path=' + encodeURIComponent(currentJsonPath));
    const data = await res.json();
    const revisions = Array.isArray(data.revisions) ? data.revisions : [];
    if (!revisions.length) {
      listEl.innerHTML = `<div style="color:var(--muted)">${t('revision_none')}</div>`;
      return;
    }
    listEl.innerHTML = '';
    revisions.forEach((rev) => {
      const rowEl = document.createElement('div');
      rowEl.className = 'revision-row';
      const note = String(rev.revision_note || '');
      const noteText = note.startsWith('before_restore#')
        ? `${t('revision_history')} #${note.split('#')[1]}`
        : t('edit_action');
      rowEl.innerHTML = `
        <div class="revision-meta">
          <span class="revision-id">#${rev.id}</span>
          <span class="revision-time">${String(rev.created_at || '')}</span>
          <span class="revision-user">${String(rev.created_by || '')}</span>
          <span class="revision-count">${rev.action_count} ${t('vanva_actions_unit')}</span>
          <span class="revision-note">${noteText}</span>
        </div>
      `;
      const btn = document.createElement('button');
      btn.className = 'btn revision-restore-btn';
      btn.textContent = t('revision_restore');
      btn.onclick = async () => {
        if (!window.confirm(t('revision_restore_confirm'))) return;
        await restoreRevision(rev.id);
      };
      rowEl.appendChild(btn);
      listEl.appendChild(rowEl);
    });
  } catch (e) {
    listEl.innerHTML = `<div style="color:var(--danger,#ef5350)">${t('revision_load_failed', { error: e.message })}</div>`;
  }
}

async function restoreRevision(revisionId) {
  try {
    const res = await authFetch('/api/result_revisions/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision_id: revisionId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'status ' + res.status);
    notify(t('revision_restored'));
    const sel = document.getElementById('reviewResultSelect');
    if (sel && sel.value) {
      sel.dispatchEvent(new Event('change'));
    }
    showRevisionHistory();
  } catch (e) {
    notify(t('revision_load_failed', { error: e.message }));
  }
}

let chartInstance = null;
let chartCountLabelPluginRegistered = false;
let currentStats = null;

function computeActionTypeStats(actions) {
  const byLabel = new Map();
  for (const act of actions || []) {
    const label = act && act.label ? String(act.label) : '';
    if (!label) continue;
    const start = Number.parseFloat(act.start_time);
    const end = Number.parseFloat(act.end_time);
    const duration = Number.isFinite(start) && Number.isFinite(end) ? Math.max(0, end - start) : 0;

    let item = byLabel.get(label);
    if (!item) {
      item = { label, count: 0, totalDuration: 0 };
      byLabel.set(label, item);
    }
    item.count += 1;
    item.totalDuration += duration;
  }
  return Array.from(byLabel.values()).map((x) => ({
    label: x.label,
    count: x.count,
    avgDuration: x.count > 0 ? x.totalDuration / x.count : 0
  }));
}

const countLabelPlugin = {
  id: 'countLabelPlugin',
  afterDatasetsDraw(chart) {
    const opts =
      (chart && chart.options && chart.options.plugins && chart.options.plugins.countLabelPlugin) ||
      {};
    const counts = Array.isArray(opts.counts) ? opts.counts : [];
    const datasetIndex = Number.isFinite(opts.datasetIndex) ? opts.datasetIndex : 0;
    const meta = chart.getDatasetMeta(datasetIndex);
    if (!meta || !meta.data) return;

    const ctx = chart.ctx;
    ctx.save();
    ctx.fillStyle = opts.color || 'rgba(255,255,255,0.9)';
    ctx.font = opts.font || '12px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';

    meta.data.forEach((bar, idx) => {
      const count = counts[idx];
      if (count === undefined || count === null) return;
      const x = bar.x;
      const y = bar.y - 4;
      ctx.fillText(String(count), x, y);
    });

    ctx.restore();
  }
};

function renderStats(stats) {
  currentStats = stats || null;
  try {
    const canvas = document.getElementById('actionChart');

    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext('2d');

    if (!stats) {
      if (chartInstance) {
        try {
          chartInstance.destroy();
        } catch {}
        chartInstance = null;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const statTotal = document.getElementById('statTotal');
      const statTypes = document.getElementById('statTypes');
      const statAvg = document.getElementById('statAvg');
      if (statTotal) statTotal.textContent = '-';
      if (statTypes) statTypes.textContent = '-';
      if (statAvg) statAvg.textContent = '-';
      return;
    }

    if (chartInstance) {
      try {
        chartInstance.destroy();
      } catch (e) {
        console.error('Destroy failed', e);
      }
    }

    if (typeof Chart === 'undefined') {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    if (!chartCountLabelPluginRegistered && typeof Chart.register === 'function') {
      Chart.register(countLabelPlugin);
      chartCountLabelPluginRegistered = true;
    }

    const perType = computeActionTypeStats(currentActions);
    const chartText = getThemeColor('--chart-text', 'rgba(255,255,255,0.92)');
    const chartAxis = getThemeColor('--chart-axis', 'rgba(255,255,255,0.85)');
    if (perType.length > 0) {
      const labels = perType.map((t) => t.label);
      const avgDurations = perType.map((t) => Number(t.avgDuration.toFixed(2)));
      const counts = perType.map((t) => t.count);

      chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: t('avg_duration_seconds'),
              data: avgDurations,
              backgroundColor: 'rgba(122, 162, 255, 0.6)',
              borderColor: 'rgba(122, 162, 255, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: false,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: {
              labels: { color: chartText }
            },
            countLabelPlugin: {
              counts,
              datasetIndex: 0,
              color: chartText
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: chartText },
              title: { display: true, text: t('avg_duration_seconds'), color: chartAxis }
            },
            x: { ticks: { color: chartText } }
          }
        }
      });
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      chartInstance = null;
    }

    const statTotal = document.getElementById('statTotal');
    const statTypes = document.getElementById('statTypes');
    const statAvg = document.getElementById('statAvg');
    if (statTotal) statTotal.textContent = stats.total_actions || stats.action_count || '-';
    if (statTypes)
      statTypes.textContent = stats.unique_action_type_count || stats.unique_action_types || '-';
    if (statAvg)
      statAvg.textContent = (stats.avg_action_duration || stats.average_duration || 0).toFixed(1) + 's';
  } catch (e) {
    console.error(e);
  }
}

function renderAdvice(advice) {
  const container = document.getElementById('adviceList');
  if (!container) return;
  if (advice && Array.isArray(advice) && advice.length > 0) {
    container.innerHTML = advice
      .map(
        (item) => `
            <div class="advice-item">${item}</div>
        `
      )
      .join('');
  } else {
    container.innerHTML = `<div style="color:var(--muted)">${t('no_advice_data')}</div>`;
  }
}

function syncActiveAction(scrollOnChange) {
  if (!elVideo || !elNowPlaying) return;
  const t = elVideo.currentTime;
  elNowPlaying.textContent = new Date(t * 1000).toISOString().substr(14, 5);

  let found = -1;
  const allow =
    currentCycleSelection && currentCycleSelection.actionIdxSet instanceof Set
      ? currentCycleSelection.actionIdxSet
      : null;
  for (let i = 0; i < currentActions.length; i++) {
    if (allow && !allow.has(i)) continue;
    const act = currentActions[i];
    const start = parseTimeFlexible(act.start_time);
    const end = parseTimeFlexible(act.end_time);
    if (t >= start && t <= end) {
      found = i;
      break;
    }
  }

  for (let i = 0; i < currentActionEls.length; i++) {
    const el = currentActionEls[i];
    if (el) el.classList.remove('active');
  }

  if (found !== -1 && currentActionEls[found]) {
    currentActionEls[found].classList.add('active');
    if (scrollOnChange && found !== activeIndex) {
      currentActionEls[found].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (elActiveAction) elActiveAction.textContent = currentActions[found]?.label || '-';
  } else {
    if (elActiveAction) elActiveAction.textContent = '-';
  }

  updateTimelineActive(found);
  activeIndex = found;
}

function setupReviewUI() {
  elVideo = document.getElementById('video');
  elActions = document.getElementById('actionsList');
  elNowPlaying = document.getElementById('nowPlaying');
  elActionCount = document.getElementById('actionCount');
  elActiveAction = document.getElementById('activeAction');

  if (elVideo) {
    window.seekVideo = (t, { play = true } = {}) => {
      if (!elVideo) return;
      const target = clampToClip(t);
      if (!Number.isFinite(target)) return;
      try {
        elVideo.currentTime = target;
      } catch {}
      if (play) {
        try {
          const p = elVideo.play();
          if (p && typeof p.catch === 'function') p.catch(() => {});
        } catch {}
      }
    };

    elVideo.addEventListener('timeupdate', () => {
      syncActiveAction(true);
      enforceClipRange();
      updateTimelinePlayhead();
    });
    elVideo.addEventListener('seeked', () => {
      enforceClipRange();
      updateTimelinePlayhead();
    });
    elVideo.addEventListener('loadedmetadata', () => {
      const d = Number(elVideo.duration);
      if (Number.isFinite(d) && d > 0 && clipStartSec !== null && clipEndSec !== null) {
        const s0 = Number(clipStartSec);
        const e0 = Number(clipEndSec);
        if (Number.isFinite(s0) && Number.isFinite(e0) && e0 > s0) {
          clipStartSec = Math.max(0, Math.min(d, s0));
          clipEndSec = Math.max(Number(clipStartSec) + 0.001, Math.min(d, e0));
        }
      }
      if (clipStartSec !== null && Number.isFinite(clipStartSec)) {
        try {
          elVideo.currentTime = Number(clipStartSec);
        } catch {}
      }
      enforceClipRange();
      updateTimelinePlayhead();
    });
  }

  const resultSel = document.getElementById('reviewResultSelect');
  if (resultSel) {
    resultSel.addEventListener('change', async (e) => {
      if (!e.target.value) return;
      try {
        clearClipRange();
        currentJsonPath = e.target.value;
        const apiUrl =
          '/api/result_details?path=' + encodeURIComponent(e.target.value) + '&ts=' + Date.now();

        const res = await authFetch(apiUrl);
        if (!res.ok)
          throw new Error(t('load_failed_with_status', { url: apiUrl, status: res.status }));
        const data = await res.json();

        const isMd = data.overview !== undefined || data.deep_dive !== undefined || data.kaizen !== undefined;

        if (isMd) {
          renderMdView(data);
          if (data.actions_table && data.actions_table.headers && data.actions_table.rows) {
            renderActionsTable(data.actions_table, data.actions || []);
          } else {
            renderActions(data.actions || []);
          }
        } else {
          renderLegacyView();

          let actions = null;
          let stats = null;
          if (Array.isArray(data)) {
            actions = data;
          } else if (data && typeof data === 'object') {
            if (Array.isArray(data.actions)) actions = data.actions;
            else if (data.model_output && Array.isArray(data.model_output.actions))
              actions = data.model_output.actions;
            else if (data.output && Array.isArray(data.output.actions)) actions = data.output.actions;

            stats = data.stats || (data.model_output && data.model_output.stats) || data.computed_stats || null;
          }

          if (!actions) {
            const keys = data && typeof data === 'object' ? Object.keys(data).join(', ') : String(typeof data);
            throw new Error(t('unknown_json_format', { keys }));
          }

          renderActions(actions);
          renderStats(stats);
          renderAdvice(data.advice || (data.model_output && data.model_output.advice) || null);
        }

        renderActionTimeline(currentActions);
        enforceClipRange();
        updateTimelinePlayhead();
        refreshStationCompareChart();

        // 阶段 3：结果查看增强 —— 缩略图 + VA/NVA 统计
        currentThumbs = [];
        fetchResultThumbs(currentJsonPath);
        renderVaNvaStats(currentActions);

        const view = document.getElementById('view-review');
        if (view) view.scrollTop = 0;
      } catch (e) {
        notify(t('load_result_failed', { error: e.message }));
      }
    });
  }

  const videoSel = document.getElementById('reviewVideoSelect');
  if (videoSel) {
    videoSel.addEventListener('change', (e) => {
      if (e.target.value && elVideo) {
        elVideo.src = withMediaToken('/' + e.target.value);
        const name = document.getElementById('videoName');
        if (name) name.textContent = e.target.value;
        autoSelectResultByVideoPrefix(e.target.value);
      }
    });
  }

  elTimeline = document.getElementById('actionTimeline');
  elTimelineSegments = document.getElementById('actionTimelineSegments');
  elTimelinePlayhead = document.getElementById('actionTimelinePlayhead');

  if (elTimeline) {
    const onPointerMove = (e) => {
      if (isBoundaryDragging) {
        adjustBoundaryFromClientX(e.clientX);
        return;
      }
      if (!isTimelineDragging) return;
      seekFromTimelineClientX(e.clientX);
    };
    const onPointerUp = (e) => {
      if (isBoundaryDragging) {
        isBoundaryDragging = false;
        if (boundaryPointerId !== null) {
          try {
            elTimeline.releasePointerCapture(boundaryPointerId);
          } catch {}
        }
        boundaryPointerId = null;
        adjustBoundaryFromClientX(e.clientX);
        draggingBoundary = null;
        persistActionsUpdate({ silentSuccess: true });
        return;
      }
      if (!isTimelineDragging) return;
      isTimelineDragging = false;
      if (timelinePointerId !== null) {
        try {
          elTimeline.releasePointerCapture(timelinePointerId);
        } catch {}
      }
      timelinePointerId = null;
      seekFromTimelineClientX(e.clientX);
    };

    elTimeline.addEventListener('pointerdown', (e) => {
      if (!elTimeline) return;
      const handle = e.target && e.target.closest ? e.target.closest('.action-timeline-handle') : null;
      if (handle) {
        const leftIdx = Number(handle.dataset.leftIndex);
        const rightIdx = Number(handle.dataset.rightIndex);
        if (!Number.isFinite(leftIdx) || !Number.isFinite(rightIdx)) return;
        isBoundaryDragging = true;
        boundaryPointerId = e.pointerId;
        draggingBoundary = { leftIdx, rightIdx, el: handle };
        try {
          elTimeline.setPointerCapture(e.pointerId);
        } catch {}
        adjustBoundaryFromClientX(e.clientX);
        return;
      }
      const seg = e.target && e.target.closest ? e.target.closest('.action-timeline-segment') : null;
      if (seg) {
        const idx = Number(seg.dataset.index);
        const act = Number.isFinite(idx) ? currentActions[idx] : null;
        if (act) normalizeActionTimeFields(act);
        const t = act ? Number.parseFloat(act.start_time) : NaN;
        if (window.seekVideo && Number.isFinite(t)) window.seekVideo(t, { play: true });
        return;
      }
      isTimelineDragging = true;
      timelinePointerId = e.pointerId;
      try {
        elTimeline.setPointerCapture(e.pointerId);
      } catch {}
      seekFromTimelineClientX(e.clientX);
    });
    elTimeline.addEventListener('pointermove', onPointerMove);
    elTimeline.addEventListener('pointerup', onPointerUp);
    elTimeline.addEventListener('pointercancel', onPointerUp);
  }

  renderActionTimeline(currentActions);
  updateTimelinePlayhead();

  const elContextMenu = document.getElementById('contextMenu');
  const elEditModal = document.getElementById('editModal');
  const btnEditAction = document.getElementById('btnEditAction');
  const btnAddAction = document.getElementById('btnAddAction');
  const btnDeleteAction = document.getElementById('btnDeleteAction');
  const btnCancelEdit = document.getElementById('btnCancelEdit');
  const btnSaveEdit = document.getElementById('btnSaveEdit');
  bindEnterToButton(elEditModal, btnSaveEdit);

  // 阶段 3：修订历史弹窗
  const btnCloseRevisions = document.getElementById('btnCloseRevisions');
  const revisionModal = document.getElementById('revisionModal');
  if (btnCloseRevisions && revisionModal) {
    btnCloseRevisions.onclick = () => revisionModal.classList.remove('open');
    revisionModal.addEventListener('click', (e) => {
      if (e.target === revisionModal) revisionModal.classList.remove('open');
    });
  }

  let editingActionIndex = -1;
  const minActionGap = 0.1;

  function hideContextMenu() {
    if (!elContextMenu) return;
    elContextMenu.style.display = 'none';
  }

  function showContextMenu(x, y, index) {
    if (!elContextMenu) return;
    editingActionIndex = index;
    elContextMenu.style.display = 'block';
    elContextMenu.style.left = '0px';
    elContextMenu.style.top = '0px';

    const w = elContextMenu.offsetWidth;
    const h = elContextMenu.offsetHeight;
    const maxX = window.scrollX + window.innerWidth - w - 8;
    const maxY = window.scrollY + window.innerHeight - h - 8;
    const nextX = Math.max(window.scrollX + 8, Math.min(x, maxX));
    const nextY = Math.max(window.scrollY + 8, Math.min(y, maxY));
    elContextMenu.style.left = nextX + 'px';
    elContextMenu.style.top = nextY + 'px';

    if (btnDeleteAction) {
      const disabled = currentActions.length <= 1;
      btnDeleteAction.classList.toggle('disabled', disabled);
      btnDeleteAction.setAttribute('aria-disabled', disabled ? 'true' : 'false');
    }
  }

  if (elActions) {
    elActions.addEventListener('contextmenu', (e) => {
      const item = e.target.closest('.action-item');
      if (!item) return;
      e.preventDefault();
      const idx = Number(item.dataset.actionIndex ?? item.dataset.index);
      if (!Number.isFinite(idx) || idx < 0 || idx >= currentActions.length) return;
      showContextMenu(e.pageX, e.pageY, idx);
    });
  }

  document.addEventListener('click', (e) => {
    if (!elContextMenu) return;
    if (elContextMenu.style.display === 'block' && !elContextMenu.contains(e.target)) {
      hideContextMenu();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    hideContextMenu();
    if (elEditModal) elEditModal.classList.remove('open');
    const notifyModal = document.getElementById('notifyModal');
    if (notifyModal) notifyModal.classList.remove('open');
    const revModal = document.getElementById('revisionModal');
    if (revModal) revModal.classList.remove('open');
  });

  if (elContextMenu) {
    elContextMenu.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }

  function openEditModal(index) {
    if (index < 0 || index >= currentActions.length) return;
    editingActionIndex = index;
    const act = currentActions[index];

    hideContextMenu();

    normalizeActionTimeFields(act);

    const setVal = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = value ?? '';
    };

    setVal('editIndex', act.index || index + 1);
    setVal('editStartTime', act.start_time !== undefined ? act.start_time : '');
    setVal('editEndTime', act.end_time !== undefined ? act.end_time : '');
    setVal('editLabel', act.label || '');
    setVal('editIsProcess', act.is_process || '');
    setVal('editIsMove', act.is_move || '');
    setVal('editIsCheck', act.is_check || '');
    setVal('editIsWait', act.is_wait || '');
    setVal('editIsStore', act.is_store || '');
    setVal('editValueAdded', act.value_added || '');
    setVal('editVariation', act.variation || '');
    const handsText =
      String(act.hands ?? '').trim() ||
      (String(act.left_hand ?? '').trim() || String(act.right_hand ?? '').trim()
        ? `${String(act.left_hand ?? '').trim()} / ${String(act.right_hand ?? '').trim()}`.trim()
        : '');
    setVal('editHands', handsText);

    if (elEditModal) elEditModal.classList.add('open');
  }

  if (btnEditAction)
    btnEditAction.onclick = () => {
      openEditModal(editingActionIndex);
    };

  function updateActionTimeRange(act) {
    if (!act) return;
    normalizeActionTimeFields(act);
    const startNum = parseFloat(act.start_time);
    const endNum = parseFloat(act.end_time);
    if (Number.isFinite(startNum)) act.start_time = startNum;
    if (Number.isFinite(endNum)) act.end_time = endNum;
    updateActionComputedFields(act);
  }

  function normalizeAddRange(startValue, endValue, minStart, maxEnd) {
    let start = Number.isFinite(startValue) ? startValue : 0;
    let end = Number.isFinite(endValue) ? endValue : start + minActionGap;
    const safeMin = Number.isFinite(minStart) ? minStart : start;
    const safeMax = Number.isFinite(maxEnd) ? maxEnd : end;
    if (!(end > start)) {
      start = Math.max(safeMin, Math.min(safeMax - minActionGap, start));
      end = Math.min(safeMax, start + minActionGap);
    }
    if (!Number.isFinite(start)) start = 0;
    if (!Number.isFinite(end)) end = start + minActionGap;
    return { start, end, min: safeMin, max: safeMax };
  }

  function rebuildActionIndexes() {
    currentActions.forEach((act, idx) => {
      if (act && typeof act === 'object') {
        act.index = String(idx + 1);
      }
    });
  }

  function buildNewAction(prev, next) {
    if (prev) normalizeActionTimeFields(prev);
    if (next) normalizeActionTimeFields(next);
    const prevStart = parseFloat(prev?.start_time);
    const prevEnd = parseFloat(prev?.end_time);
    const nextStart = parseFloat(next?.start_time);
    const nextEnd = parseFloat(next?.end_time);
    const range = normalizeAddRange(prevEnd, nextStart, prevStart, nextEnd);
    const cycleValue =
      String(
        (prev && prev.cycle) ||
          (next && next.cycle) ||
          (currentCycleSelection ? currentCycleSelection.cycleKey : '') ||
          '1'
      ).trim() || '1';
    const action = {
      index: '',
      label: '',
      is_process: '',
      is_move: '',
      is_check: '',
      is_wait: '',
      is_store: '',
      value_added: '',
      hands: '',
      variation: '',
      cycle: cycleValue,
      start_time: range.start,
      end_time: range.end
    };
    updateActionComputedFields(action);
    return action;
  }

  if (btnAddAction)
    btnAddAction.onclick = async () => {
      if (editingActionIndex === -1) return;
      hideContextMenu();

      const insertIndex = Math.min(
        Math.max(0, editingActionIndex + 1),
        Math.max(0, currentActions.length - 1)
      );
      const prev = currentActions[Math.max(0, insertIndex - 1)];
      const next = currentActions[insertIndex];
      const newAction = buildNewAction(prev, next);
      currentActions.splice(insertIndex, 0, newAction);
      rebuildActionIndexes();
      await persistActionsUpdate({ silentSuccess: true });
      openEditModal(insertIndex);
    };

  if (btnDeleteAction)
    btnDeleteAction.onclick = async () => {
      if (editingActionIndex === -1) return;
      if (currentActions.length <= 1) {
        notify(t('cannot_delete_last_action'));
        return;
      }
      hideContextMenu();

      const removed = currentActions.splice(editingActionIndex, 1)[0];
      normalizeActionTimeFields(removed || {});

      const next = currentActions[editingActionIndex];
      const prev = currentActions[editingActionIndex - 1];
      if (next) {
        normalizeActionTimeFields(next);
        const removedStart = parseFloat(removed?.start_time);
        const nextEnd = parseFloat(next.end_time);
        if (Number.isFinite(removedStart)) {
          const adjusted = Number.isFinite(nextEnd)
            ? Math.min(removedStart, nextEnd - minActionGap)
            : removedStart;
          next.start_time = adjusted;
          updateActionTimeRange(next);
        }
      } else if (prev) {
        normalizeActionTimeFields(prev);
        const removedEnd = parseFloat(removed?.end_time);
        const prevStart = parseFloat(prev.start_time);
        if (Number.isFinite(removedEnd)) {
          const adjusted = Number.isFinite(prevStart)
            ? Math.max(removedEnd, prevStart + minActionGap)
            : removedEnd;
          prev.end_time = adjusted;
          updateActionTimeRange(prev);
        }
      }

      rebuildActionIndexes();
      await persistActionsUpdate();
    };

  if (btnCancelEdit)
    btnCancelEdit.onclick = () => {
      if (elEditModal) elEditModal.classList.remove('open');
    };

  if (btnSaveEdit)
    btnSaveEdit.onclick = async () => {
      if (editingActionIndex === -1) return;

      const act = currentActions[editingActionIndex];
      const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : '';
      };

      const st = parseFloat(getVal('editStartTime'));
      const et = parseFloat(getVal('editEndTime'));

      // Validate time range against adjacent actions
      if (editingActionIndex > 0) {
        const prev = currentActions[editingActionIndex - 1];
        if (prev && Number.isFinite(parseFloat(prev.start_time))) {
          if (st < parseFloat(prev.start_time)) {
            notify(t('start_time_earlier_than_prev', { time: prev.start_time }));
            return;
          }
        }
      }

      if (editingActionIndex < currentActions.length - 1) {
        const next = currentActions[editingActionIndex + 1];
        if (next && Number.isFinite(parseFloat(next.end_time))) {
          if (et > parseFloat(next.end_time)) {
            notify(t('end_time_later_than_next', { time: next.end_time }));
            return;
          }
        }
      }

      if (Number.isFinite(st)) act.start_time = st;
      if (Number.isFinite(et)) act.end_time = et;
      
      // Ensure start <= end for current action
      if (act.start_time > act.end_time) {
        notify(t('start_time_later_than_end_time'));
        return;
      }
      updateActionComputedFields(act);

      // Update previous action's end time
      if (editingActionIndex > 0) {
        const prev = currentActions[editingActionIndex - 1];
        if (prev) {
          prev.end_time = act.start_time;
          updateActionComputedFields(prev);
        }
      }

      // Update next action's start time
      if (editingActionIndex < currentActions.length - 1) {
        const next = currentActions[editingActionIndex + 1];
        if (next) {
          next.start_time = act.end_time;
          updateActionComputedFields(next);
        }
      }

      act.label = getVal('editLabel');
      act.is_process = getVal('editIsProcess');
      act.is_move = getVal('editIsMove');
      act.is_check = getVal('editIsCheck');
      act.is_wait = getVal('editIsWait');
      act.is_store = getVal('editIsStore');
      act.value_added = getVal('editValueAdded');
      act.hands = getVal('editHands');
      act.variation = getVal('editVariation');

      if (elEditModal) elEditModal.classList.remove('open');
      await persistActionsUpdate();
    };
}

function setupSettingsUI() {
  const themeSelect = document.getElementById('settingsTheme');
  const langSelect = document.getElementById('settingsLang');
  let storedTheme = '';
  try {
    storedTheme = localStorage.getItem('ui_theme') || '';
  } catch {}
  const initialTheme = storedTheme === 'light' ? 'light' : 'dark';
  applyTheme(initialTheme);
  if (themeSelect) {
    themeSelect.value = initialTheme;
    themeSelect.addEventListener('change', () => {
      applyTheme(themeSelect.value);
    });
  }
  if (langSelect) {
    langSelect.value = currentLang;
    langSelect.addEventListener('change', () => {
      applyLanguage(langSelect.value);
    });
  }
}

function setupCalculatorUI() {
  const btnCalc = document.getElementById('btnDoCalculate');
  if (!btnCalc) return;
  btnCalc.addEventListener('click', () => {
    const inputTokens = parseFloat(document.getElementById('calcInputTokens')?.value) || 0;
    const outputTokens = parseFloat(document.getElementById('calcOutputTokens')?.value) || 0;

    const inputPricePer1k = 0.004;
    const outputPricePer1k = 0.021;

    const inputCost = (inputTokens / 1000) * inputPricePer1k;
    const outputCost = (outputTokens / 1000) * outputPricePer1k;
    const totalCost = inputCost + outputCost;

    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    setText('resInputCost', '¥' + inputCost.toFixed(4));
    setText('resOutputCost', '¥' + outputCost.toFixed(4));
    setText('resTotalCost', '¥' + totalCost.toFixed(4));

    const res = document.getElementById('calcResult');
    if (res) res.style.display = 'block';
  });
}

async function loadPartials() {
  const targets = Array.from(document.querySelectorAll('[data-include]'));
  if (!targets.length) return;
  await Promise.all(
    targets.map(async (el) => {
      const url = el.getAttribute('data-include');
      if (!url) return;
      const res = await fetch(url, { cache: 'no-cache' });
      if (!res.ok)
        throw new Error(t('load_failed_with_status', { url, status: res.status }));
      el.innerHTML = await res.text();
    })
  );
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadPartials();
  } catch (e) {
    console.error(e);
    notify(t('page_load_failed', { error: e.message }));
  }

  applyLanguage(getStoredLang());
  initSidebar();
  setupAuthUI();
  setupUserManagement();
  setupDetectionUI();
  setupReviewUI();
  setupSettingsUI();
  setupCalculatorUI();
  setupScopeUI();
  setupOrgUI();

  loadVideoList();
  loadResultList();
});
