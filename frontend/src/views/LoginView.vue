<template>
  <div class="login-wrap">
    <!-- 画布背景动画：白底 + 柔和色浮动圆自然漂移 -->
    <canvas ref="canvasRef" class="login-canvas" aria-hidden="true" />
    <el-card class="login-card" shadow="always">
      <h1 class="title">JMTEST</h1>
      <el-form label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-button class="btn" type="primary" native-type="submit" :loading="loading">
          {{ loading ? "登录中..." : "登录" }}
        </el-button>
      </el-form>
      <el-alert v-if="errorMessage" class="error" :title="errorMessage" type="error" show-icon :closable="false" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const canvasRef = ref<HTMLCanvasElement | null>(null);
let animationId = 0;
let stopCanvas: (() => void) | null = null;

// 登录表单数据
const form = reactive({
  username: "admin",
  password: "admin12345"
});

const loading = ref(false);
const errorMessage = ref<string>("");

const router = useRouter();
const authStore = useAuthStore();

/** 白色底画布动画：柔和色浮动圆自然漂移 */
function runCanvasAnimation() {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const resize = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener("resize", resize);

  // 柔和配色：极淡的蓝、薰衣草、暖白
  const colors = [
    "rgba(228, 238, 252, 0.72)",
    "rgba(242, 236, 252, 0.68)",
    "rgba(248, 250, 252, 0.78)",
    "rgba(236, 244, 252, 0.65)",
    "rgba(250, 248, 255, 0.7)"
  ];
  const circles: { x: number; y: number; r: number; vx: number; vy: number; color: string }[] = [];
  const count = 12;
  for (let i = 0; i < count; i++) {
    circles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: 60 + Math.random() * 120,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      color: colors[i % colors.length]
    });
  }

  const loop = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const c of circles) {
      c.x += c.vx;
      c.y += c.vy;
      if (c.x < -c.r) c.x = canvas.width + c.r;
      if (c.x > canvas.width + c.r) c.x = -c.r;
      if (c.y < -c.r) c.y = canvas.height + c.r;
      if (c.y > canvas.height + c.r) c.y = -c.r;
      ctx.beginPath();
      ctx.arc(c.x, c.y, c.r, 0, Math.PI * 2);
      ctx.fillStyle = c.color;
      ctx.fill();
    }
    animationId = requestAnimationFrame(loop);
  };
  loop();

  stopCanvas = () => {
    window.removeEventListener("resize", resize);
    cancelAnimationFrame(animationId);
  };
}

onMounted(() => {
  document.body.classList.add("login-page");
  runCanvasAnimation();
});

onUnmounted(() => {
  document.body.classList.remove("login-page");
  stopCanvas?.();
});

async function handleLogin() {
  errorMessage.value = "";
  loading.value = true;
  try {
    await authStore.login({ username: form.username, password: form.password });
    await router.push({ name: "Home" });
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || e?.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
/* 整页不出现滚动条，白底 */
.login-wrap {
  position: fixed;
  inset: 0;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafbfc;
}

/* 画布铺满，置于底层 */
.login-canvas {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  display: block;
  z-index: 0;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 420px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(16, 24, 40, 0.06);
}

.title {
  margin: 0 0 18px;
  font-size: 20px;
  font-weight: 700;
}

.btn {
  width: 100%;
  margin-top: 6px;
}

.error {
  margin: 10px 0 0;
  color: #b42318;
  font-size: 13px;
}
</style>

