import { defineStore } from "pinia";

import { api, unwrap } from "../api/client";

type AuthUser = {
  id: number;
  real_name: string;
  username: string | null;
  role_id: number;
  status: string;
};

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("portal_admin_token") || "",
    user: null as AuthUser | null,
  }),
  actions: {
    async login(username: string, password: string) {
      const payload = await unwrap<{ access_token: string; user: AuthUser }>(
        api.post("/auth/login/password", { username, password }),
      );
      this.token = payload.access_token;
      this.user = payload.user;
      localStorage.setItem("portal_admin_token", payload.access_token);
    },
    async restore() {
      if (!this.token) return;
      try {
        this.user = await unwrap<AuthUser>(api.get("/auth/me"));
      } catch {
        this.logout();
      }
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem("portal_admin_token");
    },
  },
});
