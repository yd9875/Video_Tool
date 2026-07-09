const state = {
  currentProjectId: null,
  projects: [],
  messages: [],
  scenes: [],
  attachments: [],
  generatedFiles: [],
  scriptFiles: [],
  contentTypeLocked: false,
  aiTasks: [],
  isHydrating: false,
  saveTimer: null,
};

const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

const elements = {
  projectList: $("#projectList"),
  newProject: $("#newProject"),
  projectTitle: $("#projectTitle"),
  platform: $("#platform"),
  durationMinutes: $("#durationMinutes"),
  durationSeconds: $("#durationSeconds"),
  briefInput: $("#briefInput"),
  contentTypeInputs: $$('input[name="contentType"]'),
  longformOptions: $("#longformOptions"),
  longformModeInputs: $$('input[name="longformMode"]'),
  attachmentInput: $("#attachmentInput"),
  attachmentDrop: $(".attachment-drop"),
  attachmentList: $("#attachmentList"),
  generatedFileList: $("#generatedFileList"),
  scriptPanel: $("#scriptPanel"),
  scriptRequirements: $("#scriptRequirements"),
  generateScript: $("#generateScript"),
  scriptFileList: $("#scriptFileList"),
  modeLabel: $("#modeLabel"),
  messages: $("#messages"),
  chatForm: $("#chatForm"),
  chatInput: $("#chatInput"),
  generateOnePage: $("#generateOnePage"),
  suggestPrompt: $("#suggestPrompt"),
  sceneList: $("#sceneList"),
  sceneCount: $("#sceneCount"),
  storySummary: $("#storySummary"),
  addScene: $("#addScene"),
  saveProject: $("#saveProject"),
  copyStoryboard: $("#copyStoryboard"),
  exportStoryboard: $("#exportStoryboard"),
  resetProject: $("#resetProject"),
  saveStatus: $("#saveStatus"),
  aiTaskList: $("#aiTaskList"),
  sceneTemplate: $("#sceneTemplate"),
  chatProviderInput: $("#chatProviderInput"),
  chatApiKeyInput: $("#chatApiKeyInput"),
  chatModelInput: $("#chatModelInput"),
  imageProviderInput: $("#imageProviderInput"),
  imageApiKeyInput: $("#imageApiKeyInput"),
  imageModelInput: $("#imageModelInput"),
  saveApiKey: $("#saveApiKey"),
  clearApiKey: $("#clearApiKey"),
  apiStatus: $("#apiStatus"),
};

const defaultBrief = "";
const API_BASE = location.protocol === "file:" ? "http://127.0.0.1:8020" : "";
const platformOptions = [
  "Instagram Reels",
  "Instagram Feed",
  "TikTok",
  "YouTube Shorts",
  "YouTube In-stream",
  "YouTube Long Form",
];
const chatApiKeyStorageKey = "conti_ai_openai_api_key";
const chatProviderStorageKey = "conti_ai_chat_provider";
const chatModelStorageKey = "conti_ai_openai_model";
const imageApiKeyStorageKey = "conti_ai_openai_image_api_key";
const imageProviderStorageKey = "conti_ai_image_provider";
const imageModelStorageKey = "conti_ai_openai_image_model";
const chatModelOptions = {
  openai: [
    ["gpt-5.5", "GPT-5.5"],
    ["gpt-5-mini", "GPT-5 mini"],
    ["gpt-5", "GPT-5"],
    ["gpt-5-nano", "GPT-5 nano"],
    ["gpt-4.1-mini", "GPT-4.1 mini"],
  ],
  openrouter: [
    ["openai/gpt-5-mini", "OpenAI GPT-5 mini"],
    ["openai/gpt-5", "OpenAI GPT-5"],
    ["anthropic/claude-sonnet-5", "Claude Sonnet 5"],
    ["google/gemini-3.5-flash", "Gemini 3.5 Flash"],
  ],
  anthropic: [
    ["claude-fable-5", "Claude Fable 5"],
    ["claude-opus-4-8", "Claude Opus 4.8"],
    ["claude-sonnet-5", "Claude Sonnet 5"],
    ["claude-haiku-4-5", "Claude Haiku 4.5"],
  ],
  gemini: [
    ["gemini-3.5-flash", "Gemini 3.5 Flash"],
    ["gemini-3.5-pro", "Gemini 3.5 Pro"],
    ["gemini-2.5-flash", "Gemini 2.5 Flash"],
  ],
};
const imageModelOptions = {
  openai: [
    ["gpt-image-2", "GPT Image 2"],
    ["gpt-image-1.5", "GPT Image 1.5"],
    ["gpt-image-1", "GPT Image 1"],
    ["gpt-image-1-mini", "GPT Image 1 mini"],
  ],
  gemini: [
    ["gemini-3.1-flash-lite-image", "Nano Banana 2 Lite"],
    ["gemini-3.1-flash-image", "Nano Banana 2"],
    ["gemini-3-pro-image", "Nano Banana Pro"],
    ["gemini-2.5-flash-image", "Nano Banana"],
  ],
};

function formatDuration(minutes, seconds) {
  const minuteValue = clampInteger(minutes, 0, 999);
  const secondValue = clampInteger(seconds, 0, 59);
  if (minuteValue <= 0 && secondValue <= 0) return "0초";
  if (minuteValue <= 0) return `${secondValue}초`;
  if (secondValue <= 0) return `${minuteValue}분`;
  return `${minuteValue}분 ${secondValue}초`;
}

function clampInteger(value, min, max) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function parseDuration(value = "15초") {
  const text = String(value);
  const minuteMatch = text.match(/(\d+)\s*분/);
  const secondMatch = text.match(/(\d+)\s*초/);
  let minutes = minuteMatch ? Number(minuteMatch[1]) : 0;
  let seconds = secondMatch ? Number(secondMatch[1]) : 0;

  if (!minuteMatch && secondMatch && seconds >= 60) {
    minutes = Math.floor(seconds / 60);
    seconds = seconds % 60;
  }

  minutes = clampInteger(minutes, 0, 999);
  seconds = clampInteger(seconds, 0, 59);
  return { minutes, seconds };
}

function getDuration() {
  normalizeDurationInputs();
  return formatDuration(elements.durationMinutes.value, elements.durationSeconds.value);
}

function setDuration(value) {
  const { minutes, seconds } = parseDuration(value);
  elements.durationMinutes.value = String(minutes);
  elements.durationSeconds.value = String(seconds);
}

function durationToSeconds(value) {
  const { minutes, seconds } = parseDuration(value);
  return minutes * 60 + seconds;
}

function normalizeDurationInputs() {
  elements.durationMinutes.value = String(clampInteger(elements.durationMinutes.value, 0, 999));
  elements.durationSeconds.value = String(clampInteger(elements.durationSeconds.value, 0, 59));
}

const sampleScenes = [
  {
    title: "출근길 정지 화면",
    visual: "지하철 플랫폼. 손목시계가 8:47을 가리키고, 주인공은 잠이 덜 깬 얼굴로 폰을 확인한다.",
    copy: "아침이 너무 빨리 왔다면",
    note: "첫 1초는 무음에 가깝게 시작하고, 알림 진동 소리로 시선을 끈다.",
    image: "",
  },
  {
    title: "한 모금 전환",
    visual: "가방 옆 포켓에서 작은 콜드브루 병을 꺼낸다. 뚜껑이 열리며 차가운 수증기가 짧게 보인다.",
    copy: "한 모금으로 켜지는 출근 모드",
    note: "제품 클로즈업은 2초 이내. 병 라벨이 정면으로 보이게 잡는다.",
    image: "",
  },
  {
    title: "색이 돌아오는 도시",
    visual: "주인공이 걷기 시작하자 회색빛 거리가 선명한 색으로 바뀐다. 발걸음과 비트가 맞아떨어진다.",
    copy: "가볍게, 진하게, 바로",
    note: "속도감 있는 점프컷. 과한 설명 대신 표정 변화와 리듬으로 설득한다.",
    image: "",
  },
  {
    title: "자연스러운 구매 유도",
    visual: "엘리베이터 앞에서 병을 다시 가방에 넣고 미소 짓는다. 화면 하단에 구매 버튼 UI가 떠오른다.",
    copy: "오늘 아침은 콜드브루로 시작",
    note: "CTA는 마지막 2초만 노출. 플랫폼 기본 버튼과 겹치지 않게 중앙보다 살짝 위에 배치한다.",
    image: "",
  },
];

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return map[char];
  });
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

function loadApiSettings() {
  const savedChatProvider = localStorage.getItem(chatProviderStorageKey) || "openai";
  const savedChatKey = localStorage.getItem(chatApiKeyStorageKey) || "";
  const savedChatModel = localStorage.getItem(chatModelStorageKey) || "gpt-5-mini";
  const savedImageProvider = localStorage.getItem(imageProviderStorageKey) || "openai";
  const savedImageKey = localStorage.getItem(imageApiKeyStorageKey) || "";
  const savedImageModel = localStorage.getItem(imageModelStorageKey) || "gpt-image-1";
  elements.chatProviderInput.value = savedChatProvider;
  elements.chatApiKeyInput.value = savedChatKey;
  renderChatModelOptions(savedChatProvider, savedChatModel);
  elements.imageProviderInput.value = savedImageProvider;
  elements.imageApiKeyInput.value = savedImageKey;
  renderImageModelOptions(savedImageProvider, savedImageModel);
  updateApiStatus();
}

function renderChatModelOptions(provider, selectedValue) {
  const options = chatModelOptions[provider] || chatModelOptions.openai;
  elements.chatModelInput.innerHTML = options
    .map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`)
    .join("");
  setSelectValue(elements.chatModelInput, selectedValue || options[0][0], "저장된 모델");
}

function renderImageModelOptions(provider, selectedValue) {
  const options = imageModelOptions[provider] || imageModelOptions.openai;
  elements.imageModelInput.innerHTML = options
    .map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`)
    .join("");
  setSelectValue(elements.imageModelInput, selectedValue || options[0][0], "저장된 모델");
}

function updateApiStatus(text) {
  if (text) {
    elements.apiStatus.textContent = text;
    return;
  }
  const hasChatKey = elements.chatApiKeyInput.value.trim();
  const hasImageKey = elements.imageApiKeyInput.value.trim() || hasChatKey;
  if (hasChatKey && hasImageKey) {
    elements.apiStatus.textContent = `${getChatProviderLabel()} 대화/이미지 모델 준비`;
  } else if (hasChatKey) {
    elements.apiStatus.textContent = `${getChatProviderLabel()} 대화 모델 준비`;
  } else {
    elements.apiStatus.textContent = "로컬 모드";
  }
}

function setSelectValue(select, value, labelPrefix) {
  if ([...select.options].some((option) => option.value === value)) {
    select.value = value;
    return;
  }
  const option = document.createElement("option");
  option.value = value;
  option.textContent = `${labelPrefix}: ${value}`;
  select.appendChild(option);
  select.value = value;
}

function getChatProviderLabel() {
  const selected = elements.chatProviderInput.selectedOptions[0];
  return selected ? selected.textContent.replace(" 준비 중", "") : "OpenAI";
}

function isSceneRequest(userText) {
  const lower = userText.toLowerCase();
  const compact = lower.replace(/\s/g, "");
  const mentionsIdeaBoard = compact.includes("아이디어보드") || compact.includes("ideaboard");
  const requestsStandaloneFileOrImage = [
    "이미지",
    "그림",
    "파일",
    "pdf",
    "txt",
    "스케치",
    "원페이지",
    "대본",
    "다운로드",
  ].some((word) => compact.includes(word));
  const mentionsSceneField = [
    "장면",
    "화면",
    "연출",
    "연출메모",
    "자막",
    "대사",
    "카피",
    "visual",
    "copy",
    "note",
    "scene",
  ].some((word) => compact.includes(word));
  const actionWords = [
    "생성",
    "만들",
    "작성",
    "짜",
    "구성해",
    "수정",
    "고쳐",
    "바꿔",
    "변경",
    "개선",
    "보완",
    "반영",
    "적용",
    "업데이트",
  ];
  const hasAction = actionWords.some((word) => compact.includes(word));
  if (!mentionsIdeaBoard && requestsStandaloneFileOrImage) return false;
  return (mentionsIdeaBoard || (state.scenes.length > 0 && mentionsSceneField)) && hasAction;
}

function saveApiSettings() {
  const chatProvider = elements.chatProviderInput.value || "openai";
  const chatKey = elements.chatApiKeyInput.value.trim();
  const chatModel = elements.chatModelInput.value.trim() || "gpt-5-mini";
  const imageProvider = elements.imageProviderInput.value || "openai";
  const imageKey = elements.imageApiKeyInput.value.trim();
  const imageModel = elements.imageModelInput.value.trim() || imageModelOptions[imageProvider]?.[0]?.[0] || "gpt-image-1";
  localStorage.setItem(chatProviderStorageKey, chatProvider);
  if (chatKey) localStorage.setItem(chatApiKeyStorageKey, chatKey);
  else localStorage.removeItem(chatApiKeyStorageKey);
  if (imageKey) localStorage.setItem(imageApiKeyStorageKey, imageKey);
  else localStorage.removeItem(imageApiKeyStorageKey);
  localStorage.setItem(chatModelStorageKey, chatModel);
  localStorage.setItem(imageProviderStorageKey, imageProvider);
  localStorage.setItem(imageModelStorageKey, imageModel);
  elements.chatModelInput.value = chatModel;
  elements.imageModelInput.value = imageModel;
  updateApiStatus(chatKey ? "AI 설정 저장됨" : "로컬 모드");
}

function clearApiSettings() {
  localStorage.removeItem(chatProviderStorageKey);
  localStorage.removeItem(chatApiKeyStorageKey);
  localStorage.removeItem(imageApiKeyStorageKey);
  localStorage.removeItem(imageProviderStorageKey);
  elements.chatApiKeyInput.value = "";
  elements.imageApiKeyInput.value = "";
  elements.chatProviderInput.value = "openai";
  elements.imageProviderInput.value = "openai";
  renderChatModelOptions("openai", "gpt-5-mini");
  renderImageModelOptions("openai", "gpt-image-1");
  updateApiStatus("키 삭제됨");
}

function setSaveStatus(text, tone = "idle") {
  elements.saveStatus.textContent = text;
  elements.saveStatus.dataset.tone = tone;
}

function renderAiTasks() {
  if (!state.aiTasks.length) {
    elements.aiTaskList.innerHTML = "";
    elements.aiTaskList.hidden = true;
    syncProjectActionLocks();
    return;
  }

  elements.aiTaskList.hidden = false;
  elements.aiTaskList.innerHTML = state.aiTasks
    .map(
      (task) => `
        <div class="ai-task ${task.status}" data-task-id="${escapeHtml(task.id)}">
          <span class="ai-task-dot" aria-hidden="true"></span>
          <span>${escapeHtml(task.label)}</span>
          <strong>${escapeHtml(task.statusText)}</strong>
          ${
            task.status === "running"
              ? ""
              : `<button class="ai-task-ack" type="button" data-task-id="${escapeHtml(task.id)}">확인</button>`
          }
        </div>
      `
    )
    .join("");
  $$(".ai-task-ack", elements.aiTaskList).forEach((button) => {
    button.addEventListener("click", () => dismissAiTask(button.dataset.taskId));
  });
  syncProjectActionLocks();
}

function startAiTask(id, label) {
  const existing = state.aiTasks.find((task) => task.id === id);
  if (existing) {
    existing.label = label;
    existing.status = "running";
    existing.statusText = "진행 중";
    window.clearTimeout(existing.removeTimer);
  } else {
    state.aiTasks.push({ id, label, status: "running", statusText: "진행 중", removeTimer: null });
  }
  renderAiTasks();
}

function finishAiTask(id, statusText = "완료", status = "done") {
  const task = state.aiTasks.find((item) => item.id === id);
  if (!task) return;
  task.status = status;
  task.statusText = statusText;
  window.clearTimeout(task.removeTimer);
  task.removeTimer = null;
  renderAiTasks();
}

function dismissAiTask(id) {
  state.aiTasks = state.aiTasks.filter((item) => item.id !== id);
  renderAiTasks();
}

function isAiTaskRunning(id) {
  return state.aiTasks.some((task) => task.id === id && task.status === "running");
}

function onePageTaskId(projectId) {
  return projectId ? `onepage-${projectId}` : "";
}

function scriptTaskId(projectId) {
  return projectId ? `script-${projectId}` : "";
}

function syncProjectActionLocks() {
  elements.generateOnePage.disabled = isAiTaskRunning(onePageTaskId(state.currentProjectId));
  elements.generateScript.disabled = isAiTaskRunning(scriptTaskId(state.currentProjectId));
}

function projectPayload() {
  return {
    title: elements.projectTitle.value.trim() || "제목 없는 콘티",
    platform: elements.platform.value,
    duration: getDuration(),
    contentType: getContentType(),
    longformMode: getLongformMode(),
    brief: elements.briefInput.value.trim(),
    messages: state.messages,
    scenes: state.scenes,
    attachments: state.attachments,
    generatedFiles: state.generatedFiles,
    scriptFiles: state.scriptFiles,
    contentTypeLocked: state.contentTypeLocked,
  };
}

function getBrief() {
  return {
    title: elements.projectTitle.value.trim() || "제목 없는 콘티",
    platform: elements.platform.value,
    duration: getDuration(),
    contentType: getContentType(),
    longformMode: getLongformMode(),
    brief: elements.briefInput.value.trim(),
  };
}

function getContentType() {
  return elements.contentTypeInputs.find((input) => input.checked)?.value || "범용 콘티";
}

function getLongformMode() {
  return getContentType() === "롱폼 (홍보영상, 인터뷰 등)"
    ? elements.longformModeInputs.find((input) => input.checked)?.value || "Narration only"
    : "";
}

function setContentType(value = "범용 콘티") {
  const nextValue = [...elements.contentTypeInputs].some((input) => input.value === value) ? value : "범용 콘티";
  elements.contentTypeInputs.forEach((input) => {
    input.checked = input.value === nextValue;
  });
  updateLongformOptions();
}

function setLongformMode(value = "Narration only") {
  const nextValue = [...elements.longformModeInputs].some((input) => input.value === value) ? value : "Narration only";
  elements.longformModeInputs.forEach((input) => {
    input.checked = input.value === nextValue;
  });
}

function syncContentTypeLock() {
  elements.contentTypeInputs.forEach((input) => {
    input.disabled = state.contentTypeLocked;
  });
  elements.longformModeInputs.forEach((input) => {
    input.disabled = state.contentTypeLocked;
  });
}

function updateLongformOptions() {
  const isLongform = getContentType() === "롱폼 (홍보영상, 인터뷰 등)";
  elements.longformOptions.hidden = !isLongform;
  elements.scriptPanel.hidden = !isLongform;
  syncContentTypeLock();
}

function getSketchAspect() {
  const contentType = getContentType();
  if (contentType === "숏폼 (보도자료 등)") return "9:16";
  if (contentType === "롱폼 (홍보영상, 인터뷰 등)") return "16:9";
  return "16:9";
}

function getSketchAspectForProject(project = {}) {
  if (project.contentType === "숏폼 (보도자료 등)") return "9:16";
  if (project.contentType === "롱폼 (홍보영상, 인터뷰 등)") return "16:9";
  return "16:9";
}

function scheduleSave() {
  if (state.isHydrating) return;
  window.clearTimeout(state.saveTimer);
  if (!state.currentProjectId) {
    setSaveStatus("저장 필요", "pending");
    return;
  }
  setSaveStatus("저장 대기", "pending");
  state.saveTimer = window.setTimeout(saveCurrentProject, 450);
}

async function saveCurrentProject() {
  try {
    setSaveStatus("저장 중", "pending");
    const isNewProject = !state.currentProjectId;
    const saved = await api(isNewProject ? "/api/projects" : `/api/projects/${state.currentProjectId}`, {
      method: isNewProject ? "POST" : "PUT",
      body: JSON.stringify(projectPayload()),
    });
    state.currentProjectId = saved.id;
    upsertProjectSummary(saved);
    renderProjectList();
    setSaveStatus("저장됨", "saved");
  } catch (error) {
    console.error(error);
    setSaveStatus(`저장 실패: ${error.message}`, "error");
  }
}

function projectTitleLabel(project = {}) {
  return String(project.title || "제목 없는 프로젝트").trim() || "제목 없는 프로젝트";
}

function projectsByExactTitle(title) {
  const normalizedTitle = String(title || "").trim();
  if (!normalizedTitle) return [];
  return state.projects.filter((project) => String(project.title || "").trim() === normalizedTitle);
}

function resolveProjectIdByExactTitle(title) {
  const matches = projectsByExactTitle(title);
  return matches.length === 1 ? matches[0].id : null;
}

async function createProjectTaskContext() {
  window.clearTimeout(state.saveTimer);
  const projectIdAtStart = state.currentProjectId;
  const previousContentTypeLock = state.contentTypeLocked;
  state.contentTypeLocked = true;
  syncContentTypeLock();
  const payload = { ...projectPayload(), id: projectIdAtStart };
  const titleMatches = projectIdAtStart ? [] : projectsByExactTitle(payload.title);
  if (!projectIdAtStart && titleMatches.length > 1) {
    state.contentTypeLocked = false;
    syncContentTypeLock();
    throw new Error("동일한 제목의 프로젝트가 여러 개 있습니다. 프로젝트 목록에서 작업할 프로젝트를 다시 선택한 뒤 AI 작업을 실행해주세요.");
  }
  const resolvedProjectId = projectIdAtStart || resolveProjectIdByExactTitle(payload.title);
  setSaveStatus("AI 작업용 프로젝트 저장 중", "pending");
  let saved;
  try {
    saved = await api(resolvedProjectId ? `/api/projects/${resolvedProjectId}` : "/api/projects", {
      method: resolvedProjectId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
  } catch (error) {
    state.contentTypeLocked = previousContentTypeLock;
    syncContentTypeLock();
    throw error;
  }
  const project = { ...payload, ...saved, id: saved.id };
  upsertProjectSummary(saved);
  if (state.currentProjectId === projectIdAtStart || (!projectIdAtStart && resolvedProjectId)) {
    state.currentProjectId = saved.id;
    renderProjectList();
    setSaveStatus("저장됨", "saved");
  } else {
    renderProjectList();
  }
  return {
    projectId: saved.id,
    projectTitle: projectTitleLabel(project),
    project,
  };
}

function mergeGeneratedFiles(files, existingFiles = []) {
  if (!Array.isArray(files) || files.length === 0) return existingFiles;
  const normalized = files.map(normalizeGeneratedFile).filter((file) => file.content.trim());
  if (!normalized.length) return existingFiles;
  return [...normalized, ...existingFiles.map(normalizeGeneratedFile)].slice(0, 20);
}

async function updateProjectData(projectId, updater) {
  const baseProject =
    state.currentProjectId === projectId ? { ...projectPayload(), id: projectId } : await api(`/api/projects/${projectId}`);
  const nextProject = updater(baseProject) || baseProject;
  const saved = await api(`/api/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(nextProject),
  });
  upsertProjectSummary(saved);
  if (state.currentProjectId === projectId) {
    hydrateProject(saved);
  } else {
    renderProjectList();
  }
  return saved;
}

function appendProjectMessage(project, role, text) {
  project.messages = Array.isArray(project.messages) ? project.messages : [];
  project.messages.push({ role, text });
  return project;
}

function upsertProjectSummary(project) {
  const summary = {
    id: project.id,
    title: project.title,
    platform: project.platform,
    duration: project.duration,
    updatedAt: project.updatedAt,
  };
  const index = state.projects.findIndex((item) => item.id === project.id);
  if (index >= 0) state.projects[index] = summary;
  else state.projects.unshift(summary);
  state.projects.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
}

function renderProjectList() {
  if (state.projects.length === 0) {
    elements.projectList.innerHTML = '<div class="empty-state">저장된 프로젝트가 없습니다.</div>';
    return;
  }

  elements.projectList.innerHTML = state.projects
    .map((project) => {
      const isActive = project.id === state.currentProjectId;
      const updated = formatDate(project.updatedAt);
      return `
        <div class="project-item ${isActive ? "active" : ""}" data-project-id="${project.id}">
          <button class="project-open" type="button" data-project-id="${project.id}">
            <strong>${escapeHtml(project.title)}</strong>
            <span>${escapeHtml(project.platform)} · ${escapeHtml(project.duration)} · ${updated}</span>
          </button>
          <button class="project-delete" type="button" data-project-id="${project.id}" aria-label="${escapeHtml(project.title)} 삭제">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 6h18"></path>
              <path d="M8 6V4h8v2"></path>
              <path d="M19 6l-1 14H6L5 6"></path>
            </svg>
          </button>
        </div>
      `;
    })
    .join("");

  $$(".project-open", elements.projectList).forEach((button) => {
    button.addEventListener("click", () => loadProject(button.dataset.projectId));
  });

  $$(".project-delete", elements.projectList).forEach((button) => {
    button.addEventListener("click", () => deleteProject(button.dataset.projectId));
  });
}

function formatDate(value) {
  if (!value) return "방금";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "방금";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatDateTime(value) {
  if (!value) return "생성시각 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "생성시각 없음";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function blankProject() {
  return {
    id: null,
    title: "",
    platform: "Instagram Reels",
    duration: "15초",
    brief: "",
    contentType: "범용 콘티",
    longformMode: "Narration only",
    messages: [],
    scenes: [],
    attachments: [],
    generatedFiles: [],
    scriptFiles: [],
    contentTypeLocked: false,
  };
}

function hydrateProject(project) {
  state.isHydrating = true;
  state.currentProjectId = project.id;
  state.messages = Array.isArray(project.messages) ? project.messages : [];
  state.scenes = Array.isArray(project.scenes) ? project.scenes : [];
  state.attachments = Array.isArray(project.attachments) ? project.attachments : [];
  state.generatedFiles = Array.isArray(project.generatedFiles) ? project.generatedFiles.map(normalizeGeneratedFile) : [];
  state.scriptFiles = Array.isArray(project.scriptFiles) ? project.scriptFiles.map(normalizeScriptFile) : [];
  state.contentTypeLocked = Boolean(project.contentTypeLocked);

  elements.projectTitle.value = project.title ?? "";
  elements.platform.value = platformOptions.includes(project.platform) ? project.platform : "Instagram Reels";
  setDuration(project.duration || "15초");
  setContentType(project.contentType || "범용 콘티");
  setLongformMode(project.longformMode || "Narration only");
  updateLongformOptions();
  syncContentTypeLock();
  elements.briefInput.value = project.brief ?? defaultBrief;

  elements.modeLabel.textContent = "작업 유형, 브리프, 첨부 파일, 장면을 함께 분석";

  renderMessages();
  renderAttachments();
  renderGeneratedFiles();
  renderScriptFiles();
  renderScenes();
  renderProjectList();
  syncProjectActionLocks();
  setSaveStatus(project.id ? "저장됨" : "저장 필요", project.id ? "saved" : "pending");
  state.isHydrating = false;
}

async function loadProject(id) {
  try {
    setSaveStatus("불러오는 중", "pending");
    const project = await api(`/api/projects/${id}`);
    hydrateProject(project);
  } catch (error) {
    console.error(error);
    setSaveStatus("불러오기 실패", "error");
  }
}

async function deleteProject(id) {
  const project = state.projects.find((item) => item.id === id);
  const title = project?.title || "이 프로젝트";
  if (!window.confirm(`"${title}" 프로젝트를 삭제할까요?`)) return;

  try {
    setSaveStatus("삭제 중", "pending");
    await api(`/api/projects/${id}`, { method: "DELETE" });
    state.projects = state.projects.filter((item) => item.id !== id);
    if (state.currentProjectId === id) {
      startNewProject();
    } else {
      renderProjectList();
      setSaveStatus("삭제됨", "saved");
    }
  } catch (error) {
    console.error(error);
    setSaveStatus(`삭제 실패: ${error.message}`, "error");
  }
}

function startNewProject() {
  hydrateProject(blankProject());
}

async function boot() {
  try {
    const projects = await api("/api/projects");
    state.projects = projects;
    renderProjectList();
    startNewProject();
  } catch (error) {
    console.error(error);
    setSaveStatus("서버 연결 실패", "error");
    hydrateProject({
      id: null,
      title: "",
      platform: "Instagram Reels",
      duration: "15초",
      brief: defaultBrief,
      contentType: "범용 콘티",
      longformMode: "Narration only",
      messages: [],
      scenes: [],
      attachments: [],
      generatedFiles: [],
      scriptFiles: [],
      contentTypeLocked: false,
    });
  }
}

function addMessage(role, text) {
  state.messages.push({ role, text });
  renderMessages();
  scheduleSave();
}

function renderMessages() {
  elements.messages.innerHTML = state.messages
    .map(
      (message) => `
        <article class="message ${message.role}">
          <div class="message-role">${message.role === "user" ? "나" : "AI"}</div>
          <div class="message-bubble">${escapeHtml(message.text).replaceAll("\n", "<br>")}</div>
        </article>
      `
    )
    .join("");
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function createScene(overrides = {}) {
  return {
    title: overrides.title || "새 장면",
    visual: overrides.visual || "화면 구도를 적어주세요.",
    copy: overrides.copy || "자막 또는 대사를 적어주세요.",
    note: overrides.note || "카메라, 사운드, 전환 메모를 적어주세요.",
    image: overrides.image || "",
  };
}

function ensureSceneShape(scene) {
  return {
    title: scene.title || "새 장면",
    visual: scene.visual || "",
    copy: scene.copy || "",
    note: scene.note || "",
    image: scene.image || "",
  };
}

function renderScenePreview(node, scene, index) {
  const preview = $(".scene-preview", node);
  if (scene.image) {
    preview.innerHTML = `
      <button class="scene-image-open" type="button" aria-label="이미지 새 탭에서 열기">
        <img src="${scene.image}" alt="${escapeHtml(scene.title || "장면 이미지")}" />
      </button>
      <button class="scene-image-save" type="button" aria-label="이미지 저장">저장</button>
    `;
    $(".scene-image-open", preview).addEventListener("click", () => {
      openImageInNewTab(scene.image, scene.title || "장면 이미지");
    });
    $(".scene-image-save", preview).addEventListener("click", (event) => {
      event.stopPropagation();
      downloadSceneImage(scene.image, index);
    });
  } else {
    preview.innerHTML = '<div class="empty-preview">이미지 없음</div>';
  }
}

function safeFilename(value = "project") {
  return String(value)
    .replace(/[\\/:*?"<>|]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function sceneImageFilename(index) {
  const title = safeFilename(elements.projectTitle.value || "제목 없는 프로젝트") || "제목 없는 프로젝트";
  const sceneNumber = String(index + 1).padStart(2, "0");
  return `${title} - ${sceneNumber}.png`;
}

async function downloadSceneImage(src, index) {
  const filename = sceneImageFilename(index);
  const link = document.createElement("a");
  link.download = filename;

  if (src.startsWith("data:")) {
    link.href = src;
    link.click();
    return;
  }

  try {
    const response = await fetch(src);
    if (!response.ok) throw new Error(`Image download failed: ${response.status}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error(error);
    link.href = src;
    link.target = "_blank";
    link.click();
  }
}

function openImageInNewTab(src, title) {
  const opened = window.open("", "_blank");
  if (!opened) return;

  const safeSrc = escapeHtml(src);
  const safeTitle = escapeHtml(title);
  opened.document.open();
  opened.document.write(`<!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8" />
        <title>${safeTitle}</title>
        <style>
          html, body {
            margin: 0;
            min-height: 100%;
            background: #151716;
          }
          body {
            display: grid;
            place-items: center;
            padding: 24px;
          }
          img {
            display: block;
            max-width: 100%;
            max-height: calc(100vh - 48px);
            object-fit: contain;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.36);
          }
        </style>
      </head>
      <body>
        <img src="${safeSrc}" alt="${safeTitle}" />
      </body>
    </html>`);
  opened.document.close();
}

async function generateSceneSketch(index, node) {
  const apiKey = elements.imageApiKeyInput.value.trim() || elements.chatApiKeyInput.value.trim();
  if (!apiKey) {
    updateApiStatus("AI 스케치에는 API 키가 필요합니다");
    setSaveStatus("API 키 필요", "error");
    return;
  }

  let context;
  try {
    context = await createProjectTaskContext();
  } catch (error) {
    console.error(error);
    setSaveStatus(error.message, "error");
    return;
  }

  const scene = context.project.scenes?.[index];
  if (!scene) return;

  const button = $(".ai-sketch", node);
  const preview = $(".scene-preview", node);
  const model = elements.imageModelInput.value.trim() || "gpt-image-1";
  const taskId = `sketch-${context.projectId}-${index}`;
  button.disabled = true;
  button.textContent = "생성 중";
  preview.innerHTML = '<div class="empty-preview loading">AI 스케치 생성 중</div>';
  updateApiStatus("AI 스케치 생성 중");
  setSaveStatus("AI 스케치 생성 중", "pending");
  startAiTask(taskId, `${context.projectTitle} - ${index + 1}번 장면 AI 스케치`);

  try {
    const result = await api("/api/ai/sketch", {
      method: "POST",
      body: JSON.stringify({
        apiKey,
        provider: elements.imageProviderInput.value || "openai",
        model,
        aspect: getSketchAspectForProject(context.project),
        sceneIndex: index,
        scene,
        project: context.project,
      }),
    });
    await updateProjectData(context.projectId, (project) => {
      project.scenes = Array.isArray(project.scenes) ? project.scenes : [];
      project.scenes[index] = ensureSceneShape(project.scenes[index] || scene);
      project.scenes[index].image = result.image;
      return project;
    });
    updateApiStatus("AI 스케치 완료");
    setSaveStatus("AI 스케치 완료", "saved");
    finishAiTask(taskId, "완료", "done");
  } catch (error) {
    console.error(error);
    if (state.currentProjectId === context.projectId && document.body.contains(node)) {
      renderScenePreview(node, state.scenes[index], index);
    }
    updateApiStatus(`AI 스케치 오류: ${error.message}`);
    setSaveStatus("AI 스케치 실패", "error");
    finishAiTask(taskId, "실패", "error");
  } finally {
    if (document.body.contains(node)) {
      button.disabled = false;
      button.textContent = state.scenes[index]?.image ? "AI 스케치 다시" : "AI 스케치";
    }
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file, "utf-8");
  });
}

function getAttachmentKind(file) {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("audio/")) return "audio";
  if (file.type === "application/pdf" || /\.pdf$/i.test(file.name)) return "pdf";
  if (file.type.startsWith("text/") || /\.(txt|md|csv|json)$/i.test(file.name)) return "text";
  return "file";
}

function formatFileSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

async function addAttachments(files) {
  const largeFileWarningSize = 25 * 1024 * 1024;
  let addedCount = 0;
  for (const file of files) {
    if (file.size > largeFileWarningSize) {
      setSaveStatus(`대용량 파일 첨부 중: ${file.name}`, "pending");
    }

    try {
      const kind = getAttachmentKind(file);
      const attachment = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name: file.name,
        type: file.type || "application/octet-stream",
        kind,
        size: file.size,
        text: "",
        dataUrl: "",
      };

      if (kind === "text") {
        attachment.text = (await readFileAsText(file)).slice(0, 220000);
      } else {
        attachment.dataUrl = await readFileAsDataUrl(file);
      }

      state.attachments.push(attachment);
      addedCount += 1;
    } catch (error) {
      console.error(error);
      setSaveStatus(`첨부 실패: ${file.name}`, "error");
    }
  }

  renderAttachments();
  if (addedCount > 0) {
    setSaveStatus(`${addedCount}개 파일 첨부됨`, "pending");
    scheduleSave();
  }
}

function renderAttachments() {
  if (!state.attachments.length) {
    elements.attachmentList.innerHTML = '<div class="empty-state">첨부된 파일이 없습니다.</div>';
    return;
  }

  elements.attachmentList.innerHTML = state.attachments
    .map(
      (file) => `
        <div class="attachment-item" data-attachment-id="${escapeHtml(file.id)}">
          <div>
            <strong>${escapeHtml(file.name)}</strong>
            <span>${escapeHtml(file.kind)} · ${escapeHtml(file.type || "unknown")} · ${formatFileSize(file.size || 0)}${file.text ? " · 본문 있음" : ""}</span>
          </div>
          <div class="attachment-actions">
            ${
              file.kind === "audio"
                ? `<button class="button secondary attachment-transcribe" type="button" data-attachment-id="${escapeHtml(file.id)}">${file.text ? "재전사" : "전사"}</button>`
                : ""
            }
            <button class="icon-button small attachment-remove" type="button" aria-label="${escapeHtml(file.name)} 삭제">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 6h18"></path>
                <path d="M8 6V4h8v2"></path>
                <path d="M19 6l-1 14H6L5 6"></path>
              </svg>
            </button>
          </div>
        </div>
      `
    )
    .join("");

  $$(".attachment-transcribe", elements.attachmentList).forEach((button) => {
    button.addEventListener("click", () => transcribeAttachment(button.dataset.attachmentId));
  });

  $$(".attachment-remove", elements.attachmentList).forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.closest(".attachment-item")?.dataset.attachmentId;
      state.attachments = state.attachments.filter((file) => file.id !== id);
      renderAttachments();
      scheduleSave();
    });
  });
}

async function transcribeAttachment(id) {
  let context;
  try {
    context = await createProjectTaskContext();
  } catch (error) {
    console.error(error);
    setSaveStatus(error.message, "error");
    return;
  }

  const attachment = context.project.attachments?.find((file) => file.id === id);
  if (!attachment || attachment.kind !== "audio") return;

  const apiKey = getTranscriptionApiKey();
  if (!apiKey) {
    updateApiStatus("오디오 전사에는 OpenAI API 키가 필요합니다");
    setSaveStatus("API 키 필요", "error");
    return;
  }

  const taskId = `transcribe-${context.projectId}-${id}`;
  startAiTask(taskId, `${context.projectTitle} - ${attachment.name} 전사`);
  updateApiStatus("오디오 전사 중");
  setSaveStatus("오디오 전사 중", "pending");
  renderAttachments();

  try {
    await transcribeAudioAttachment(attachment, apiKey);
    await updateProjectData(context.projectId, (project) => {
      project.attachments = Array.isArray(project.attachments) ? project.attachments : [];
      const index = project.attachments.findIndex((file) => file.id === id);
      if (index >= 0) project.attachments[index] = attachment;
      return project;
    });
    updateApiStatus("오디오 전사 완료");
    setSaveStatus("오디오 전사 완료", "saved");
    finishAiTask(taskId, "완료", "done");
  } catch (error) {
    console.error(error);
    updateApiStatus(`전사 오류: ${error.message}`);
    setSaveStatus("오디오 전사 실패", "error");
    finishAiTask(taskId, "실패", "error");
  }
}

function getTranscriptionApiKey() {
  if (elements.chatProviderInput.value === "openai") {
    return elements.chatApiKeyInput.value.trim();
  }
  if (elements.imageProviderInput.value === "openai") {
    return elements.imageApiKeyInput.value.trim() || elements.chatApiKeyInput.value.trim();
  }
  return elements.chatApiKeyInput.value.trim();
}

async function transcribeAudioAttachment(attachment, apiKey) {
  const result = await api("/api/ai/transcribe", {
    method: "POST",
    body: JSON.stringify({ apiKey, attachment }),
  });
  attachment.text = result.text || "";
  return attachment.text;
}

async function ensureAudioTranscriptions() {
  const pendingAudio = state.attachments.filter((file) => file.kind === "audio" && !String(file.text || "").trim());
  if (!pendingAudio.length) return;

  const apiKey = getTranscriptionApiKey();
  if (!apiKey) {
    throw new Error("오디오를 읽으려면 OpenAI API 키로 먼저 전사해야 합니다.");
  }

  for (const attachment of pendingAudio) {
    const taskId = `transcribe-${attachment.id}`;
    startAiTask(taskId, `${attachment.name} 자동 전사`);
    updateApiStatus("오디오 자동 전사 중");
    setSaveStatus("오디오 자동 전사 중", "pending");
    try {
      await transcribeAudioAttachment(attachment, apiKey);
      finishAiTask(taskId, "완료", "done");
    } catch (error) {
      finishAiTask(taskId, "실패", "error");
      throw new Error(`${attachment.name} 전사 실패: ${error.message}`);
    }
  }

  renderAttachments();
  scheduleSave();
}

async function ensureAudioTranscriptionsForContext(context) {
  context.project.attachments = Array.isArray(context.project.attachments) ? context.project.attachments : [];
  const pendingAudio = context.project.attachments.filter((file) => file.kind === "audio" && !String(file.text || "").trim());
  if (!pendingAudio.length) return;

  const apiKey = getTranscriptionApiKey();
  if (!apiKey) {
    throw new Error("오디오를 읽으려면 OpenAI API 키로 먼저 전사해야 합니다.");
  }

  for (const attachment of pendingAudio) {
    const taskId = `transcribe-${context.projectId}-${attachment.id}`;
    startAiTask(taskId, `${context.projectTitle} - ${attachment.name} 자동 전사`);
    updateApiStatus("오디오 자동 전사 중");
    setSaveStatus("오디오 자동 전사 중", "pending");
    try {
      await transcribeAudioAttachment(attachment, apiKey);
      finishAiTask(taskId, "완료", "done");
    } catch (error) {
      finishAiTask(taskId, "실패", "error");
      throw new Error(`${attachment.name} 전사 실패: ${error.message}`);
    }
  }

  await updateProjectData(context.projectId, (project) => {
    project.attachments = context.project.attachments;
    return project;
  });
}

function sanitizeGeneratedFileType(value = "txt") {
  return String(value || "txt")
    .toLowerCase()
    .replace(/[^a-z0-9.+_-]/g, "")
    .slice(0, 32) || "txt";
}

function generatedFileExtension(type, mimeType = "") {
  const cleanType = sanitizeGeneratedFileType(type);
  const knownExtensions = {
    image: "png",
    txt: "txt",
    pdf: "pdf",
    md: "md",
    csv: "csv",
    json: "json",
    html: "html",
    xml: "xml",
    docx: "docx",
    xlsx: "xlsx",
    pptx: "pptx",
    zip: "zip",
  };
  if (knownExtensions[cleanType]) return knownExtensions[cleanType];

  const mimeExtensions = {
    "application/json": "json",
    "text/markdown": "md",
    "text/csv": "csv",
    "text/html": "html",
    "application/xml": "xml",
    "text/xml": "xml",
  };
  const explicitMime = String(mimeType || "").toLowerCase();
  if (mimeExtensions[explicitMime]) return mimeExtensions[explicitMime];

  const suffix = cleanType.includes("+") ? cleanType.split("+").pop() : cleanType;
  return suffix.replace(/[^a-z0-9]/g, "").slice(0, 12) || "bin";
}

function generatedFileMimeType(type, mimeType = "") {
  const explicitMime = String(mimeType || "").trim();
  if (explicitMime.includes("/")) return explicitMime;
  const cleanType = sanitizeGeneratedFileType(type);
  const knownMimeTypes = {
    image: "image/png",
    txt: "text/plain",
    pdf: "application/pdf",
    md: "text/markdown",
    csv: "text/csv",
    json: "application/json",
    html: "text/html",
    xml: "application/xml",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    zip: "application/zip",
  };
  return knownMimeTypes[cleanType] || "application/octet-stream";
}

function hasFileExtension(name) {
  return /\.[a-z0-9][a-z0-9.+_-]{0,15}$/i.test(name);
}

function normalizeGeneratedFile(file = {}) {
  const type = sanitizeGeneratedFileType(file.type || "txt");
  const mimeType = generatedFileMimeType(type, file.mimeType);
  const extension = generatedFileExtension(type, mimeType);
  const fallbackName = type === "image" ? "ai-image.png" : `ai-file.${extension}`;
  const rawName = String(file.name || fallbackName).trim() || fallbackName;
  const name = hasFileExtension(rawName) ? rawName : `${rawName}.${extension}`;
  const encoding = String(file.encoding || "utf8").toLowerCase() === "base64" ? "base64" : "utf8";
  return {
    id: String(file.id || `${Date.now()}-${Math.random().toString(16).slice(2)}`),
    name,
    type,
    mimeType,
    encoding,
    content: String(file.content || ""),
    createdAt: file.createdAt || new Date().toISOString(),
  };
}

function appendGeneratedFiles(files) {
  if (!Array.isArray(files) || files.length === 0) return false;
  const normalized = files.map(normalizeGeneratedFile).filter((file) => file.content.trim());
  if (!normalized.length) return false;
  state.generatedFiles = [...normalized, ...state.generatedFiles].slice(0, 20);
  renderGeneratedFiles();
  return true;
}

function renderGeneratedFiles() {
  if (!state.generatedFiles.length) {
    elements.generatedFileList.innerHTML = '<div class="empty-state">생성된 파일이 없습니다.</div>';
    return;
  }

  elements.generatedFileList.innerHTML = state.generatedFiles
    .map(
      (file) => `
        <div class="generated-file-item" data-file-id="${escapeHtml(file.id)}">
          <div>
            <strong>${escapeHtml(file.name)}</strong>
            <span>${escapeHtml(file.type.toUpperCase())} · ${escapeHtml(file.encoding)} · 생성시각 ${escapeHtml(formatDateTime(file.createdAt))}</span>
          </div>
          <div class="generated-file-actions">
            <button class="icon-button small generated-file-download" type="button" aria-label="${escapeHtml(file.name)} 다운로드">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <path d="M7 10l5 5 5-5"></path>
                <path d="M12 15V3"></path>
              </svg>
            </button>
            <button class="icon-button small generated-file-remove" type="button" aria-label="${escapeHtml(file.name)} 삭제">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 6h18"></path>
                <path d="M8 6V4h8v2"></path>
                <path d="M19 6l-1 14H6L5 6"></path>
              </svg>
            </button>
          </div>
        </div>
      `
    )
    .join("");

  $$(".generated-file-download", elements.generatedFileList).forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.closest(".generated-file-item")?.dataset.fileId;
      const file = state.generatedFiles.find((item) => item.id === id);
      if (file) downloadGeneratedFile(file);
    });
  });

  $$(".generated-file-remove", elements.generatedFileList).forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.closest(".generated-file-item")?.dataset.fileId;
      state.generatedFiles = state.generatedFiles.filter((file) => file.id !== id);
      renderGeneratedFiles();
      scheduleSave();
    });
  });
}

function normalizeScriptFile(file = {}) {
  const rawName = String(file.name || "script.txt").trim() || "script.txt";
  const name = rawName.toLowerCase().endsWith(".txt") ? rawName : `${rawName}.txt`;
  return {
    id: String(file.id || `${Date.now()}-${Math.random().toString(16).slice(2)}`),
    name,
    requirementsSummary: String(file.requirementsSummary || "요구사항 요약 없음"),
    content: String(file.content || ""),
    createdAt: file.createdAt || new Date().toISOString(),
  };
}

function renderScriptFiles() {
  if (!state.scriptFiles.length) {
    elements.scriptFileList.innerHTML = '<div class="empty-state">생성된 대본 파일이 없습니다.</div>';
    return;
  }

  elements.scriptFileList.innerHTML = state.scriptFiles
    .map(
      (file) => `
        <div class="generated-file-item" data-script-file-id="${escapeHtml(file.id)}">
          <div>
            <strong>${escapeHtml(file.name)}</strong>
            <span>TXT · 생성시각 ${escapeHtml(formatDateTime(file.createdAt))}</span>
            <span>요구사항: ${escapeHtml(file.requirementsSummary)}</span>
          </div>
          <div class="generated-file-actions">
            <button class="icon-button small script-file-download" type="button" aria-label="${escapeHtml(file.name)} 다운로드">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <path d="M7 10l5 5 5-5"></path>
                <path d="M12 15V3"></path>
              </svg>
            </button>
            <button class="icon-button small script-file-remove" type="button" aria-label="${escapeHtml(file.name)} 삭제">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 6h18"></path>
                <path d="M8 6V4h8v2"></path>
                <path d="M19 6l-1 14H6L5 6"></path>
              </svg>
            </button>
          </div>
        </div>
      `
    )
    .join("");

  $$(".script-file-download", elements.scriptFileList).forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.closest(".generated-file-item")?.dataset.scriptFileId;
      const file = state.scriptFiles.find((item) => item.id === id);
      if (file) downloadText(file.name, file.content);
    });
  });

  $$(".script-file-remove", elements.scriptFileList).forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.closest(".generated-file-item")?.dataset.scriptFileId;
      state.scriptFiles = state.scriptFiles.filter((file) => file.id !== id);
      renderScriptFiles();
      scheduleSave();
    });
  });
}

function renderScenes() {
  elements.sceneList.innerHTML = "";
  state.scenes.forEach((scene, index) => {
    state.scenes[index] = ensureSceneShape(scene);
    scene = state.scenes[index];
    const node = elements.sceneTemplate.content.firstElementChild.cloneNode(true);
    $(".scene-index", node).textContent = String(index + 1).padStart(2, "0");
    $(".scene-title", node).value = scene.title;
    $(".scene-visual", node).value = scene.visual;
    $(".scene-copy", node).value = scene.copy;
    $(".scene-note", node).value = scene.note;
    renderScenePreview(node, scene, index);

    $(".move-scene-up", node).disabled = index === 0;
    $(".move-scene-down", node).disabled = index === state.scenes.length - 1;

    $(".move-scene-up", node).addEventListener("click", () => moveScene(index, -1));
    $(".move-scene-down", node).addEventListener("click", () => moveScene(index, 1));

    $(".delete-scene", node).addEventListener("click", () => {
      state.scenes.splice(index, 1);
      renderScenes();
      updateSummary();
      scheduleSave();
    });

    [
      [".scene-title", "title"],
      [".scene-visual", "visual"],
      [".scene-copy", "copy"],
      [".scene-note", "note"],
    ].forEach(([selector, key]) => {
      $(selector, node).addEventListener("input", (event) => {
        state.scenes[index][key] = event.target.value;
        updateSummary();
        scheduleSave();
      });
    });

    $(".scene-image-input", node).addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) return;
      const dataUrl = await readFileAsDataUrl(file);
      state.scenes[index].image = dataUrl;
      renderScenePreview(node, state.scenes[index], index);
      scheduleSave();
    });

    const sketchButton = $(".ai-sketch", node);
    sketchButton.textContent = scene.image ? "AI 스케치 다시" : "AI 스케치";
    sketchButton.addEventListener("click", () => generateSceneSketch(index, node));

    elements.sceneList.appendChild(node);
  });

  elements.sceneCount.textContent = state.scenes.length;
  updateSummary();
}

function moveScene(index, direction) {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= state.scenes.length) return;
  const [scene] = state.scenes.splice(index, 1);
  state.scenes.splice(nextIndex, 0, scene);
  renderScenes();
  scheduleSave();
}

function updateSummary() {
  const { title, platform, duration, contentType, longformMode } = getBrief();
  const formatLabel = longformMode ? `${contentType} · ${longformMode}` : contentType;
  elements.storySummary.innerHTML = `
    <div>
      <span>프로젝트</span>
      <strong>${escapeHtml(title)}</strong>
    </div>
    <div>
      <span>매체</span>
      <strong>${escapeHtml(platform)} · ${escapeHtml(duration)}</strong>
    </div>
    <div>
      <span>작업 유형</span>
      <strong>${escapeHtml(formatLabel)}</strong>
    </div>
  `;
}

async function generateAiReply(userText, context) {
  const apiKey = elements.chatApiKeyInput.value.trim();
  if (!apiKey) return null;

  const model = elements.chatModelInput.value.trim() || "gpt-5-mini";
  localStorage.setItem(chatModelStorageKey, model);
  const taskId = `chat-reply-${context.projectId}`;
  updateApiStatus("AI 응답 생성 중");
  setSaveStatus("AI 응답 생성 중", "pending");
  startAiTask(taskId, `${context.projectTitle} - AI 대화 응답 생성`);

  try {
    await ensureAudioTranscriptionsForContext(context);
    const result = await api("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({
        apiKey,
        provider: elements.chatProviderInput.value || "openai",
        model,
        message: userText,
        project: context.project,
        imageSettings: {
          apiKey: elements.imageApiKeyInput.value.trim() || apiKey,
          provider: elements.imageProviderInput.value || "openai",
          model: elements.imageModelInput.value.trim() || "gpt-image-1",
          aspect: getSketchAspectForProject(context.project),
        },
      }),
    });

    updateApiStatus("OpenAI 연결됨");
    setSaveStatus("AI 응답 완료", "saved");
    finishAiTask(taskId, "완료", "done");
    return result;
  } catch (error) {
    finishAiTask(taskId, "실패", "error");
    throw error;
  }
}

async function generateReply(userText, context) {
  const shouldUpdateIdeaBoard = isSceneRequest(userText);
  try {
    const aiResult = await generateAiReply(userText, context);
    if (aiResult) {
      let nextScenes = null;
      let replyText = aiResult.text;
      if (shouldUpdateIdeaBoard && Array.isArray(aiResult.scenes) && aiResult.scenes.length > 0) {
        nextScenes = aiResult.scenes.map((scene) => ensureSceneShape(scene));
      } else if (shouldUpdateIdeaBoard) {
        nextScenes = tuneScenesFromBrief(context.project, userText);
        replyText = `${aiResult.text}\n\nAI 응답에서 장면 카드 구조를 읽지 못해, 현재 기준의 장면 초안을 아이디어 보드에 채웠어요.`;
      }
      await updateProjectData(context.projectId, (project) => {
        appendProjectMessage(project, "assistant", replyText);
        if (nextScenes) project.scenes = nextScenes;
        project.generatedFiles = mergeGeneratedFiles(aiResult.files, project.generatedFiles || []);
        return project;
      });
      return replyText;
    }
  } catch (error) {
    console.error(error);
    updateApiStatus(`AI 오류: ${error.message}`);
    const replyText = `AI 오류: ${error.message}`;
    await updateProjectData(context.projectId, (project) => appendProjectMessage(project, "assistant", replyText));
    return replyText;
  }

  const brief = context.project;
  const lower = userText.toLowerCase();

  if (shouldUpdateIdeaBoard) {
    const fallbackScenes = tuneScenesFromBrief(brief, userText);
    const replyText = [
      `${brief.duration} ${brief.platform} 기준으로 ${fallbackScenes.length}개 장면을 잡았어요.`,
      "초반은 문제 상황을 짧게 보여주고, 중반은 제품 경험으로 분위기를 전환하며, 마지막은 플랫폼 UI와 겹치지 않는 CTA로 닫았습니다.",
      "오른쪽 보드에서 화면, 자막, 연출 메모를 바로 고칠 수 있어요.",
    ].join("\n");
    await updateProjectData(context.projectId, (project) => {
      appendProjectMessage(project, "assistant", replyText);
      project.scenes = fallbackScenes;
      return project;
    });
    return replyText;
  }

  if (lower.includes("수정") || lower.includes("피드백") || lower.includes("개선")) {
    const replyText = [
      "좋아요. 지금 요청은 대화 안에서 검토 의견으로 정리할게요.",
      "아이디어 보드를 실제로 바꾸려면 '아이디어 보드에 반영해줘' 또는 '아이디어보드 수정해줘'처럼 보내주세요.",
    ].join("\n");
    await updateProjectData(context.projectId, (project) => appendProjectMessage(project, "assistant", replyText));
    return replyText;
  }

  const replyText = [
    "브리프를 보면 지금 아이디어 보드의 중심은 짧은 시간 안에 공감 상황을 만들고, 제품 경험으로 분위기를 전환하는 것이에요.",
    `권장 구조는 ${brief.duration} 안에서 훅 20%, 제품 경험 50%, CTA 30% 정도입니다.`,
    "바로 장면으로 펼치고 싶으면 '이 기준으로 아이디어 보드 만들어줘'라고 보내주세요.",
  ].join("\n");
  await updateProjectData(context.projectId, (project) => appendProjectMessage(project, "assistant", replyText));
  return replyText;
}

async function generateOnePageFiles() {
  const apiKey = elements.chatApiKeyInput.value.trim();
  if (!apiKey) {
    updateApiStatus("원페이지 생성에는 API 키가 필요합니다");
    setSaveStatus("API 키 필요", "error");
    return;
  }

  let context;
  try {
    context = await createProjectTaskContext();
  } catch (error) {
    console.error(error);
    setSaveStatus(error.message, "error");
    return;
  }

  const taskId = `onepage-${context.projectId}`;
  if (isAiTaskRunning(taskId)) {
    setSaveStatus("이 프로젝트의 원페이지 콘티가 이미 생성 중입니다", "pending");
    return;
  }
  updateApiStatus("원페이지 콘티 생성 중");
  setSaveStatus("원페이지 생성 중", "pending");
  startAiTask(taskId, `${context.projectTitle} - 원페이지 콘티 생성`);
  syncProjectActionLocks();

  try {
    await ensureAudioTranscriptionsForContext(context);
    const result = await api("/api/ai/onepage", {
      method: "POST",
      body: JSON.stringify({
        apiKey,
        provider: elements.chatProviderInput.value || "openai",
        model: elements.chatModelInput.value.trim() || "gpt-5-mini",
        project: context.project,
        deferImage: true,
        imageSettings: {
          apiKey: elements.imageApiKeyInput.value.trim() || apiKey,
          provider: elements.imageProviderInput.value || "openai",
          model: elements.imageModelInput.value.trim() || "gpt-image-1",
          aspect: getSketchAspectForProject(context.project),
        },
      }),
    });
    await updateProjectData(context.projectId, (project) => {
      project.generatedFiles = mergeGeneratedFiles(result.files, project.generatedFiles || []);
      appendProjectMessage(project, "assistant", result.text || "원페이지 콘티 PDF와 이미지 파일을 생성했어요.");
      return project;
    });
    updateApiStatus("원페이지 콘티 생성 완료");
    setSaveStatus("원페이지 생성 완료", "saved");
    finishAiTask(taskId, "완료", "done");
  } catch (error) {
    console.error(error);
    updateApiStatus(`원페이지 오류: ${error.message}`);
    setSaveStatus("원페이지 생성 실패", "error");
    finishAiTask(taskId, "실패", "error");
  } finally {
    syncProjectActionLocks();
  }
}

async function generateScriptFile() {
  const apiKey = elements.chatApiKeyInput.value.trim();
  if (!apiKey) {
    updateApiStatus("대본 생성에는 API 키가 필요합니다");
    setSaveStatus("API 키 필요", "error");
    return;
  }

  if (getContentType() !== "롱폼 (홍보영상, 인터뷰 등)") {
    setSaveStatus("롱폼 작업 유형에서만 대본을 생성할 수 있습니다", "error");
    return;
  }

  const requirements = elements.scriptRequirements.value.trim();
  let context;
  try {
    context = await createProjectTaskContext();
  } catch (error) {
    console.error(error);
    setSaveStatus(error.message, "error");
    return;
  }

  const taskId = scriptTaskId(context.projectId);
  if (isAiTaskRunning(taskId)) {
    setSaveStatus("이 프로젝트의 대본이 이미 생성 중입니다", "pending");
    return;
  }

  updateApiStatus("대본 생성 중");
  setSaveStatus("대본 생성 중", "pending");
  startAiTask(taskId, `${context.projectTitle} - 대본 생성`);
  syncProjectActionLocks();

  try {
    await ensureAudioTranscriptionsForContext(context);
    const result = await api("/api/ai/script", {
      method: "POST",
      body: JSON.stringify({
        apiKey,
        provider: elements.chatProviderInput.value || "openai",
        model: elements.chatModelInput.value.trim() || "gpt-5-mini",
        requirements,
        project: context.project,
      }),
    });

    const scriptFile = normalizeScriptFile({
      name: result.name,
      requirementsSummary: result.requirementsSummary,
      content: result.content,
      createdAt: result.createdAt,
    });

    await updateProjectData(context.projectId, (project) => {
      project.scriptFiles = Array.isArray(project.scriptFiles) ? project.scriptFiles.map(normalizeScriptFile) : [];
      project.scriptFiles = [scriptFile, ...project.scriptFiles].slice(0, 20);
      return project;
    });

    updateApiStatus("대본 생성 완료");
    setSaveStatus("대본 생성 완료", "saved");
    finishAiTask(taskId, "완료", "done");
  } catch (error) {
    console.error(error);
    updateApiStatus(`대본 생성 오류: ${error.message}`);
    setSaveStatus("대본 생성 실패", "error");
    finishAiTask(taskId, "실패", "error");
  } finally {
    syncProjectActionLocks();
  }
}

function tuneScenesFromBrief(brief, userText) {
  const scenes = sampleScenes.map((scene) => ({ ...scene }));
  const cleanBrief = brief.brief || "제품의 장점을 감각적으로 보여주는 광고";

  scenes[0].visual = `타깃이 바로 공감할 만한 순간으로 시작한다. ${cleanBrief.slice(0, 70)}${cleanBrief.length > 70 ? "..." : ""}`;
  scenes[1].visual = "제품을 손에 쥐고 사용하는 순간을 클로즈업한다. 질감, 온도, 소리 중 하나를 강조한다.";
  scenes[2].visual = "사용 전후의 감정 변화가 한눈에 보이도록 배경 색, 속도, 표정을 바꾼다.";
  scenes[3].copy = `${brief.platform}에서 바로 확인하기`;

  if (userText.includes("감성") || userText.includes("시네마틱")) {
    scenes[2].note = "느린 셔터감, 자연광, 여백 있는 구도로 감정선을 살린다.";
  }

  if (userText.includes("재미") || userText.includes("유머")) {
    scenes[0].copy = "출근길 정신 로그아웃";
    scenes[2].note = "표정 리액션을 크게 쓰고 컷 전환을 빠르게 가져간다.";
  }

  if (durationToSeconds(brief.duration) >= 30) {
    scenes.splice(3, 0, {
      title: "사용 이유 증명",
      visual: "제품의 장점을 한 컷 더 보여준다. 손, 장소, 상황을 바꿔 반복 사용성을 암시한다.",
      copy: "작지만 확실한 루틴",
      note: "정보는 1개만. 성분, 가격, 편의성 중 가장 강한 근거를 선택한다.",
      image: "",
    });
  }

  return scenes;
}

function strengthenStoryboard(userText) {
  if (state.scenes.length === 0) {
    state.scenes = tuneScenesFromBrief(getBrief(), userText);
    return;
  }

  const wantsHook = userText.includes("훅") || userText.includes("초반");
  const wantsCta = userText.toLowerCase().includes("cta") || userText.includes("구매") || userText.includes("마지막");

  if (wantsHook) {
    state.scenes[0].copy = "지금, 딱 한 모금이 필요한 순간";
    state.scenes[0].note = "첫 0.5초 안에 표정과 상황이 읽히게 한다. 화면 전환은 빠르게.";
  }

  if (wantsCta || !wantsHook) {
    const last = state.scenes[state.scenes.length - 1];
    last.copy = "오늘의 첫 모금, 지금 만나보기";
    last.note = "CTA는 명령형보다 제안형으로. 제품명과 버튼은 2초 이상 유지한다.";
  }
}

function buildExportText() {
  const brief = getBrief();
  const formatLabel = brief.longformMode ? `${brief.contentType} / ${brief.longformMode}` : brief.contentType;
  const sceneText = state.scenes
    .map(
      (scene, index) => `
${index + 1}. ${scene.title}
화면: ${scene.visual}
자막/대사: ${scene.copy}
연출 메모: ${scene.note}
이미지: ${scene.image ? "첨부됨" : "자동 스케치"}`
    )
    .join("\n");

  return `# ${brief.title}

플랫폼: ${brief.platform}
길이: ${brief.duration}
작업 유형: ${formatLabel}

## 브리프
${brief.brief}

## 아이디어 보드
${sceneText}
`;
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function base64ToBlob(base64, mimeType) {
  const binary = atob(base64.replace(/\s/g, ""));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType });
}

function downloadGeneratedFile(file) {
  const blob =
    file.encoding === "base64"
      ? base64ToBlob(file.content, file.mimeType)
      : new Blob([file.content], { type: `${file.mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  link.click();
  URL.revokeObjectURL(url);
}

async function generateOnePageFilesStable() {
  const apiKey = elements.chatApiKeyInput.value.trim();
  if (!apiKey) {
    updateApiStatus("원페이지 생성에는 API 키가 필요합니다");
    setSaveStatus("API 키 필요", "error");
    return;
  }

  let context;
  try {
    context = await createProjectTaskContext();
  } catch (error) {
    console.error(error);
    setSaveStatus(error.message, "error");
    return;
  }

  const taskId = onePageTaskId(context.projectId);
  if (isAiTaskRunning(taskId)) {
    setSaveStatus("이 프로젝트의 원페이지 콘티가 이미 생성 중입니다", "pending");
    return;
  }

  const imageSettings = {
    apiKey: elements.imageApiKeyInput.value.trim() || apiKey,
    provider: elements.imageProviderInput.value || "openai",
    model: elements.imageModelInput.value.trim() || "gpt-image-1",
    aspect: getSketchAspectForProject(context.project),
  };

  updateApiStatus("원페이지 콘티 생성 중");
  setSaveStatus("원페이지 생성 중", "pending");
  startAiTask(taskId, `${context.projectTitle} - 원페이지 콘티 생성`);
  syncProjectActionLocks();

  try {
    await ensureAudioTranscriptionsForContext(context);
    const result = await api("/api/ai/onepage", {
      method: "POST",
      body: JSON.stringify({
        apiKey,
        provider: elements.chatProviderInput.value || "openai",
        model: elements.chatModelInput.value.trim() || "gpt-5-mini",
        project: context.project,
        deferImage: true,
        imageSettings,
      }),
    });

    await updateProjectData(context.projectId, (project) => {
      project.generatedFiles = mergeGeneratedFiles(result.files, project.generatedFiles || []);
      appendProjectMessage(project, "assistant", result.text || "원페이지 콘티 PDF를 생성했어요. 이미지는 이어서 생성합니다.");
      return project;
    });

    if (result.imagePrompt) {
      updateApiStatus("원페이지 이미지 생성 중");
      setSaveStatus("원페이지 이미지 생성 중", "pending");
      try {
        const imageResult = await api("/api/ai/onepage-image", {
          method: "POST",
          body: JSON.stringify({
            prompt: result.imagePrompt,
            name: result.imageName || "one-page-storyboard-image.png",
            imageSettings,
          }),
        });
        await updateProjectData(context.projectId, (project) => {
          project.generatedFiles = mergeGeneratedFiles(imageResult.files, project.generatedFiles || []);
          return project;
        });
      } catch (imageError) {
        console.error(imageError);
        await updateProjectData(context.projectId, (project) => {
          project.generatedFiles = mergeGeneratedFiles(
            [
              {
                name: `${result.imageName || "one-page-storyboard-image"}.txt`,
                type: "txt",
                mimeType: "text/plain",
                encoding: "utf8",
                content: `원페이지 이미지 생성은 실패했지만 PDF는 생성되었습니다.\n\n오류: ${imageError.message}\n\n이미지 생성 프롬프트:\n${result.imagePrompt}`,
              },
            ],
            project.generatedFiles || []
          );
          appendProjectMessage(project, "assistant", `원페이지 PDF는 생성했지만 이미지 생성은 실패했어요: ${imageError.message}`);
          return project;
        });
      }
    }

    updateApiStatus("원페이지 콘티 생성 완료");
    setSaveStatus("원페이지 생성 완료", "saved");
    finishAiTask(taskId, "완료", "done");
  } catch (error) {
    console.error(error);
    updateApiStatus(`원페이지 오류: ${error.message}`);
    setSaveStatus("원페이지 생성 실패", "error");
    finishAiTask(taskId, "실패", "error");
  } finally {
    syncProjectActionLocks();
  }
}

elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = elements.chatInput.value.trim();
  if (!text) return;

  addMessage("user", text);
  elements.chatInput.value = "";
  elements.chatInput.disabled = true;

  try {
    const context = await createProjectTaskContext();
    await generateReply(text, context);
  } catch (error) {
    console.error(error);
    updateApiStatus(`AI 오류: ${error.message}`);
    setSaveStatus("AI 작업 실패", "error");
  } finally {
    elements.chatInput.disabled = false;
    elements.chatInput.focus();
  }
});

elements.suggestPrompt.addEventListener("click", async () => {
  const apiKey = elements.chatApiKeyInput.value.trim();
  const fallback = state.scenes.length
    ? "현재 장면 흐름을 기준으로 초반 훅, 중반 전환, 마지막 CTA 중 가장 약한 부분을 짚고 개선안을 제안해줘"
    : "현재 작업 유형, 브리프, 첨부 파일을 기준으로 아이디어 보드를 만들기 위한 가장 좋은 다음 질문을 제안해줘";

  if (!apiKey) {
    elements.chatInput.value = fallback;
    elements.chatInput.focus();
    updateApiStatus("API 키가 없어 기본 추천을 넣었습니다");
    return;
  }

  let context;
  try {
    context = await createProjectTaskContext();
  } catch (error) {
    console.error(error);
    elements.chatInput.value = fallback;
    elements.chatInput.focus();
    setSaveStatus(error.message, "error");
    return;
  }

  const taskId = `prompt-suggest-${context.projectId}`;
  elements.suggestPrompt.disabled = true;
  updateApiStatus("질문 추천 생성 중");
  setSaveStatus("AI 추천 생성 중", "pending");
  startAiTask(taskId, `${context.projectTitle} - AI 질문 추천`);
  try {
    const result = await api("/api/ai/suggest", {
      method: "POST",
      body: JSON.stringify({
        apiKey,
        provider: elements.chatProviderInput.value || "openai",
        model: elements.chatModelInput.value.trim() || "gpt-5-mini",
        project: context.project,
      }),
    });
    if (state.currentProjectId === context.projectId) {
      elements.chatInput.value = result.prompt || fallback;
    }
    updateApiStatus("AI 추천 완료");
    setSaveStatus("AI 추천 완료", "saved");
    finishAiTask(taskId, "완료", "done");
  } catch (error) {
    console.error(error);
    if (state.currentProjectId === context.projectId) {
      elements.chatInput.value = fallback;
    }
    updateApiStatus(`추천 오류: ${error.message}`);
    setSaveStatus("AI 추천 실패", "error");
    finishAiTask(taskId, "실패", "error");
  } finally {
    elements.suggestPrompt.disabled = false;
    elements.chatInput.focus();
  }
});

elements.addScene.addEventListener("click", () => {
  state.scenes.push(createScene());
  renderScenes();
  scheduleSave();
});

elements.newProject.addEventListener("click", startNewProject);

elements.saveProject.addEventListener("click", saveCurrentProject);

elements.saveApiKey.addEventListener("click", saveApiSettings);

elements.clearApiKey.addEventListener("click", clearApiSettings);

elements.generateOnePage.addEventListener("click", generateOnePageFilesStable);

elements.generateScript.addEventListener("click", generateScriptFile);

elements.chatProviderInput.addEventListener("change", () => {
  const options = chatModelOptions[elements.chatProviderInput.value] || chatModelOptions.openai;
  renderChatModelOptions(elements.chatProviderInput.value, options[0][0]);
  saveApiSettings();
});
elements.chatModelInput.addEventListener("change", saveApiSettings);
elements.imageProviderInput.addEventListener("change", () => {
  const options = imageModelOptions[elements.imageProviderInput.value] || imageModelOptions.openai;
  renderImageModelOptions(elements.imageProviderInput.value, options[0][0]);
  saveApiSettings();
});
elements.imageModelInput.addEventListener("change", saveApiSettings);

elements.copyStoryboard.addEventListener("click", async () => {
  const text = buildExportText();
  await navigator.clipboard.writeText(text);
  elements.copyStoryboard.lastChild.textContent = "복사됨";
  window.setTimeout(() => {
    elements.copyStoryboard.lastChild.textContent = "복사";
  }, 1200);
});

elements.exportStoryboard.addEventListener("click", () => {
  const safeTitle = getBrief().title.replace(/[\\/:*?"<>|]/g, "").trim() || "storyboard";
  downloadText(`${safeTitle}.txt`, buildExportText());
});

elements.resetProject.addEventListener("click", () => {
  state.messages = [];
  state.scenes = [];
  state.attachments = [];
  state.generatedFiles = [];
  state.scriptFiles = [];
  state.contentTypeLocked = false;
  elements.projectTitle.value = "";
  elements.briefInput.value = defaultBrief;
  elements.scriptRequirements.value = "";
  setContentType("범용 콘티");
  setLongformMode("Narration only");
  updateLongformOptions();
  syncContentTypeLock();
  renderMessages();
  renderAttachments();
  renderGeneratedFiles();
  renderScriptFiles();
  renderScenes();
  scheduleSave();
});

[elements.projectTitle, elements.platform, elements.durationMinutes, elements.durationSeconds, elements.briefInput].forEach((element) => {
  element.addEventListener("input", () => {
    updateSummary();
    scheduleSave();
  });
});

elements.contentTypeInputs.forEach((input) => {
  input.addEventListener("change", () => {
    updateLongformOptions();
    updateSummary();
    scheduleSave();
  });
});

elements.longformModeInputs.forEach((input) => {
  input.addEventListener("change", () => {
    updateSummary();
    scheduleSave();
  });
});

elements.attachmentInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;
  await addAttachments(files);
  elements.attachmentInput.value = "";
});

["dragenter", "dragover"].forEach((eventName) => {
  elements.attachmentDrop.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.attachmentDrop.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  elements.attachmentDrop.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.attachmentDrop.classList.remove("dragging");
  });
});

elements.attachmentDrop.addEventListener("drop", async (event) => {
  const files = Array.from(event.dataTransfer?.files || []);
  if (!files.length) return;
  await addAttachments(files);
});

[elements.durationMinutes, elements.durationSeconds].forEach((element) => {
  element.addEventListener("blur", () => {
    normalizeDurationInputs();
    updateSummary();
    scheduleSave();
  });
});

loadApiSettings();
boot();
