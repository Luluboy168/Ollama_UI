const { createApp, ref, onMounted, nextTick, watch, computed } = Vue;

    createApp({
      setup() {
        const sessions = ref([]);
        const messages = ref([]);
        const userInput = ref('');
        const currentSessionId = ref(null);
        const apiBase = 'http://127.0.0.1:8000';
        const selectedModel = ref(localStorage.getItem('selectedModel') || 'gemma3:1b')
        const token = ref(localStorage.getItem('token'));
        const username = ref(localStorage.getItem('username'));
        const isLoggedIn = computed(() => !!token.value);


        watch(selectedModel, (newModel) => {
          localStorage.setItem('selectedModel', newModel)
        })

        const scrollToBottom = () => {
          const chatBox = document.getElementById("chat-box");
          if (chatBox) {
            chatBox.scrollTop = chatBox.scrollHeight;
          }
        };

        const register = async () => {
          const uname = prompt("請輸入帳號：");
          const pwd = prompt("請輸入密碼：");
          if (!uname || !pwd) return;

          const form = new URLSearchParams();
          form.append("username", uname);
          form.append("password", pwd);

          const res = await fetch(`${apiBase}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: form,
          });

          if (!res.ok) {
            const err = await res.json();
            alert("註冊失敗：" + (err.detail || res.statusText));
            return;
          }

          alert("註冊成功，請登入");
        };


        const login = async () => {
          const uname = prompt("使用者名稱：");
          const pwd = prompt("密碼：");
          if (!uname || !pwd) return;

          const form = new URLSearchParams();
          form.append("username", uname);
          form.append("password", pwd);

          const res = await fetch(`${apiBase}/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: form,
          });

          if (!res.ok) {
            alert("登入失敗");
            return;
          }

          const data = await res.json();
          token.value = data.access_token;
          username.value = uname;
          localStorage.setItem("token", token.value);
          localStorage.setItem("username", uname);
          await listSessions();
        };

        const logout = () => {
          token.value = null;
          username.value = null;
          localStorage.removeItem("token");
          localStorage.removeItem("username");
          sessions.value = [];
          messages.value = [];
          currentSessionId.value = null;
        };

        const authHeader = () => ({
          Authorization: `Bearer ${token.value}`
        });

        const listSessions = async () => {
          const res = await fetch(`${apiBase}/sessions/`, {
            headers: authHeader(),
          });
          sessions.value = await res.json();
        };

        const createSession = async () => {
          const title = prompt("聊天室標題？") || "新聊天室";
          if (!title) return;
          await fetch(`${apiBase}/sessions/`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...authHeader() },
            body: JSON.stringify({ title }),
          });
          await listSessions();
        };

        const editSession = async (id, oldTitle) => {
          const newTitle = prompt("修改聊天室標題：", oldTitle);
          if (!newTitle || newTitle.trim() === oldTitle) return;
          await fetch(`${apiBase}/sessions/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: newTitle.trim() }),
          });
          await listSessions();
        };

        const loadSession = async (id) => {
          currentSessionId.value = id;
          const res = await fetch(`${apiBase}/msgs/${id}`, {
            headers: authHeader(),
          });
          messages.value = await res.json();
          setTimeout(() => {
            const chatBox = document.getElementById("chat-box");
            if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
          }, 100);
        };

        const deleteSession = async(id) => {
          if(!confirm("Delete chat?")) return;

          await fetch(`${apiBase}/sessions/${id}`, {
            method: "DELETE",
            headers: authHeader(),
          });

          if(currentSessionId.value === id){
            currentSessionId.value = null;
            messages.value = [];
          }

          await listSessions();
        }

        const sendMessage = async () => {
          const text = userInput.value.trim();
          if (!text || !currentSessionId.value) return;
          userInput.value = '';

          messages.value.push({ role: 'user', content: text });

          const response = await fetch(`${apiBase}/msgs/${currentSessionId.value}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_msg: text, model: selectedModel.value }),
          });
          const assistantMsg = { role: 'assistant', content: '' };
          messages.value = [...messages.value];
          await nextTick();
          scrollToBottom();

          messages.value.push(assistantMsg);
          const reader = response.body.getReader();
          const decoder = new TextDecoder("utf-8");

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            assistantMsg.content += decoder.decode(value, { stream: true });

            // Force Vue to re-render by triggering reactivity
            messages.value = [...messages.value];
            scrollToBottom();
          } 
        };

        onMounted(() => {
          if (token.value) {
            listSessions();
          }
        });

        return { sessions, messages, userInput, currentSessionId, editSession,
           createSession, loadSession, deleteSession, sendMessage, selectedModel,
           register, login, logout, isLoggedIn, username };
      }
    }).mount('#app');