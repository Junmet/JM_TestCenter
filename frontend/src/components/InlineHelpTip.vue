<!-- 行末小图标 + el-tooltip -->
<template>
  <el-tooltip
    placement="top"
    effect="dark"
    :max-width="maxWidth"
    :show-after="120"
  >
    <template #content>
      <div class="help-tip-content">
        <slot />
      </div>
    </template>
    <span
      class="inline-help-trigger"
      :class="`inline-help-trigger--${variant}`"
      role="button"
      tabindex="0"
      aria-label="说明"
    >
      <el-icon :size="iconSize">
        <WarningFilled v-if="variant === 'warning'" />
        <InfoFilled v-else />
      </el-icon>
    </span>
  </el-tooltip>
</template>

<script setup lang="ts">
import { InfoFilled, WarningFilled } from "@element-plus/icons-vue";

withDefaults(
  defineProps<{
    variant?: "default" | "warning";
    maxWidth?: number;
    /** 图标像素尺寸，默认 14 */
    iconSize?: number;
  }>(),
  {
    variant: "default",
    maxWidth: 440,
    iconSize: 14,
  },
);
</script>

<style scoped>
.inline-help-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
  cursor: default;
  color: #909399;
  vertical-align: middle;
  transition: color 0.15s;
}
.inline-help-trigger:hover {
  color: #606266;
}
.inline-help-trigger--warning {
  color: #e6a23c;
}
.inline-help-trigger--warning:hover {
  color: #cf9236;
}
.help-tip-content {
  line-height: 1.55;
  font-size: 12px;
  text-align: left;
}
.help-tip-content :deep(strong) {
  font-weight: 600;
}
.help-tip-content :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.12);
}
</style>
