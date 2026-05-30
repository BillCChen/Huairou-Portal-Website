<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { adminUsersApi, getApiErrorMessage, type AdminUserCreatePayload } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

type RoleOption = {
  id: number;
  code: string;
  name: string;
  description?: string;
};

type AdminUserRow = {
  id: number;
  username: string | null;
  mobile: string | null;
  email: string | null;
  real_name: string;
  organization: string | null;
  expertise: string | null;
  status: string;
  role_id: number;
  role_code?: string | null;
  role_name?: string | null;
  created_at: string;
};

const users = ref<AdminUserRow[]>([]);
const roles = ref<RoleOption[]>([]);
const roleDrafts = ref<Record<number, string>>({});
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const statusFilter = ref("");
const loading = ref(false);
const createDialogVisible = ref(false);
const creating = ref(false);
const passwordPolicyHint = "密码需为 8–20 位，并至少包含大写字母、小写字母、数字、特殊字符中的 3 类；不能使用常见弱密码，不能与用户名、邮箱或手机号等账号信息明显相似。";
const rejectReasonHint = "请填写审核未通过原因，不少于 20 字。该说明将发送给申请人。";

const createForm = reactive<AdminUserCreatePayload>({
  username: "",
  email: "",
  mobile: "",
  real_name: "",
  organization: "",
  expertise: "",
  password: "",
  role_code: "institute_editor",
});

const createRoleCodes = new Set(["registered_user", "institute_editor"]);

const createRoleOptions = computed(() => roles.value.filter((role) => createRoleCodes.has(role.code)));

const loadRoles = async () => {
  roles.value = await adminUsersApi.listRoles();
  if (!createRoleOptions.value.some((role) => role.code === createForm.role_code)) {
    createForm.role_code = createRoleOptions.value[0]?.code || "registered_user";
  }
};

const load = async () => {
  loading.value = true;
  try {
    const data = await adminUsersApi.list({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
    });
    users.value = data.items;
    total.value = data.total;
    roleDrafts.value = Object.fromEntries(
      data.items.map((item) => [item.id, item.role_code || roleCodeById(item.role_id) || "registered_user"]),
    );
  } finally {
    loading.value = false;
  }
};

const roleCodeById = (roleId: number) => {
  return roles.value.find((role) => role.id === roleId)?.code;
};

const roleName = (row: AdminUserRow) => {
  return row.role_name || roles.value.find((role) => role.code === row.role_code || role.id === row.role_id)?.name || row.role_code || row.role_id;
};

const resetCreateForm = () => {
  createForm.username = "";
  createForm.email = "";
  createForm.mobile = "";
  createForm.real_name = "";
  createForm.organization = "";
  createForm.expertise = "";
  createForm.password = "";
  createForm.role_code = createRoleOptions.value[0]?.code || "institute_editor";
};

const createUser = async () => {
  if (!createForm.username || !createForm.real_name || !createForm.password) {
    ElMessage.error("请填写用户名、姓名和初始密码");
    return;
  }
  creating.value = true;
  try {
    const payload: AdminUserCreatePayload = {
      username: createForm.username,
      email: createForm.email || null,
      mobile: createForm.mobile || null,
      real_name: createForm.real_name,
      organization: createForm.organization || null,
      expertise: createForm.expertise || null,
      password: createForm.password,
      role_code: createForm.role_code,
    };
    await adminUsersApi.create(payload);
    ElMessage.success("机构用户已创建");
    createDialogVisible.value = false;
    resetCreateForm();
    await load();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, "创建用户失败"));
  } finally {
    creating.value = false;
  }
};

const approve = async (id: number) => {
  try {
    await adminUsersApi.approve(id);
    ElMessage.success("审核通过");
    await load();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, "审核失败"));
  }
};

const reject = async (id: number) => {
  try {
    const result = await ElMessageBox.prompt(rejectReasonHint, "驳回注册申请", {
      confirmButtonText: "驳回",
      cancelButtonText: "取消",
      inputPlaceholder: "请填写具体原因，不少于 20 字",
      inputType: "textarea",
      inputValidator: (value) => (value || "").trim().length >= 20,
      inputErrorMessage: "审核未通过原因不少于 20 字",
    });
    const reason = (result.value || "").trim();
    if (reason.length < 20) {
      ElMessage.error("审核未通过原因不少于 20 字");
      return;
    }
    await adminUsersApi.reject(id, reason);
    ElMessage.success("已驳回");
    await load();
  } catch (error) {
    if (error === "cancel" || error === "close") return;
    ElMessage.error(getApiErrorMessage(error, "驳回失败"));
  }
};

const disableUser = async (id: number) => {
  try {
    await ElMessageBox.confirm("禁用后该用户将无法登录，确认继续？", "禁用用户", {
      confirmButtonText: "禁用",
      cancelButtonText: "取消",
      type: "warning",
    });
    await adminUsersApi.disable(id);
    ElMessage.success("已禁用");
    await load();
  } catch (error) {
    if (error === "cancel" || error === "close") return;
    ElMessage.error(getApiErrorMessage(error, "禁用失败"));
  }
};

const enableUser = async (id: number) => {
  try {
    await adminUsersApi.enable(id);
    ElMessage.success("已启用");
    await load();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, "启用失败"));
  }
};

const updateRole = async (row: AdminUserRow) => {
  const roleCode = roleDrafts.value[row.id];
  if (!roleCode || roleCode === row.role_code) return;
  try {
    await adminUsersApi.updateRole(row.id, roleCode);
    ElMessage.success("角色已更新");
    await load();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, "角色更新失败"));
  }
};

const statusLabel = (status: string) => {
  const labelMap: Record<string, string> = {
    pending: "待审核",
    active: "已启用",
    rejected: "已驳回",
    disabled: "已禁用",
    inactive: "未启用",
  };
  return labelMap[status] || status;
};

const statusType = (status: string) => {
  const typeMap: Record<string, "success" | "warning" | "info" | "danger"> = {
    pending: "warning",
    active: "success",
    rejected: "danger",
    disabled: "info",
  };
  return typeMap[status] || "info";
};

const formatCreatedAt = (value: string) => {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
};

const handleFilterChange = async () => {
  page.value = 1;
  await load();
};

onMounted(async () => {
  await loadRoles();
  await load();
});
</script>

<template>
  <AppLayout>
    <div>
      <div style="font-size: 30px; font-weight: 700;">用户生命周期</div>
      <div style="margin-top: 8px; color: #64748b;">个人注册进入待审核，管理员可完成审核、禁用、恢复、机构账号创建和角色分配。</div>
    </div>

    <div style="display: flex; justify-content: space-between; gap: 16px; margin-top: 20px;">
      <el-button type="primary" @click="createDialogVisible = true">创建机构用户</el-button>
      <el-select v-model="statusFilter" placeholder="状态" style="width: 180px;" @change="handleFilterChange">
        <el-option label="全部" value="" />
        <el-option label="待审核" value="pending" />
        <el-option label="已启用" value="active" />
        <el-option label="已驳回" value="rejected" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="users" style="margin-top: 24px;">
      <el-table-column prop="username" label="用户名" min-width="150" />
      <el-table-column prop="real_name" label="姓名" min-width="130" />
      <el-table-column prop="organization" label="单位" min-width="190" />
      <el-table-column prop="email" label="邮箱" min-width="190" />
      <el-table-column prop="mobile" label="手机号" min-width="150" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="角色" min-width="230">
        <template #default="{ row }">
          <div v-if="row.status === 'active'" style="display: flex; gap: 8px; align-items: center;">
            <el-select v-model="roleDrafts[row.id]" size="small" style="width: 145px;">
              <el-option v-for="role in roles" :key="role.code" :label="role.name" :value="role.code" />
            </el-select>
            <el-button size="small" plain :disabled="roleDrafts[row.id] === row.role_code" @click="updateRole(row)">
              保存
            </el-button>
          </div>
          <span v-else>{{ roleName(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="155">
        <template #default="{ row }">
          {{ formatCreatedAt(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <el-button v-if="row.status === 'pending'" type="primary" size="small" @click="approve(row.id)">
              通过
            </el-button>
            <el-button v-if="row.status === 'pending'" type="danger" plain size="small" @click="reject(row.id)">
              驳回
            </el-button>
            <el-button v-if="row.status === 'active'" type="warning" plain size="small" @click="disableUser(row.id)">
              禁用
            </el-button>
            <el-button v-if="row.status === 'disabled'" type="success" plain size="small" @click="enableUser(row.id)">
              启用
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div style="display: flex; justify-content: flex-end; margin-top: 20px;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="prev, pager, next, total"
        :total="total"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="createDialogVisible" title="创建机构用户" width="560px" @closed="resetCreateForm">
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="createForm.real_name" autocomplete="off" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="createForm.organization" autocomplete="off" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" autocomplete="off" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="createForm.mobile" autocomplete="off" />
        </el-form-item>
        <el-form-item label="专业领域">
          <el-input v-model="createForm.expertise" autocomplete="off" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role_code" style="width: 100%;">
            <el-option v-for="role in createRoleOptions" :key="role.code" :label="role.name" :value="role.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="createForm.password" type="password" show-password autocomplete="new-password" />
          <div style="margin-top: 6px; color: #64748b; font-size: 12px; line-height: 1.5;">
            {{ passwordPolicyHint }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createUser">创建</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>
