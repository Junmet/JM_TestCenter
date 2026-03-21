<!-- Params / Headers 等：启用 + Key + Value + 说明 -->
<template>
  <div class="kv-wrap">
    <el-table :data="model" border size="small" class="kv-table">
      <el-table-column width="52" align="center">
        <template #header>启用</template>
        <template #default="{ row }">
          <el-checkbox v-model="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="Key" min-width="120">
        <template #default="{ row }">
          <el-input v-model="row.key" size="small" placeholder="键" />
        </template>
      </el-table-column>
      <el-table-column label="Value" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.value" size="small" placeholder="值" />
        </template>
      </el-table-column>
      <el-table-column label="说明" min-width="100">
        <template #default="{ row }">
          <el-input v-model="row.description" size="small" placeholder="可选" />
        </template>
      </el-table-column>
      <el-table-column width="64" align="center" fixed="right">
        <template #default="{ $index }">
          <el-button type="danger" link size="small" @click="remove($index)">删</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-button class="kv-add" size="small" @click="add">添加行</el-button>
  </div>
</template>

<script setup lang="ts">
import type { KvRow } from "./apiTestTypes";

const model = defineModel<KvRow[]>({ required: true });

function genUid() {
  return `row-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function add() {
  model.value.push({
    id: genUid(),
    enabled: true,
    key: "",
    value: "",
    description: "",
  });
}

function remove(index: number) {
  model.value.splice(index, 1);
}
</script>

<style scoped>
.kv-wrap {
  width: 100%;
}
.kv-add {
  margin-top: 8px;
}
.kv-table {
  width: 100%;
}
</style>
