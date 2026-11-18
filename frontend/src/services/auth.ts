/** ログイン・新規登録。API（/api/auth/...）を呼ぶ。ログインの状態はクッキーで持つ。 */
import { authApi, type User } from './api';

export interface AuthService { signIn(email?: string, password?: string): Promise<User>; signUp(email?: string, password?: string): Promise<User>; }
/** デモでは、メールアドレスとパスワードを両方とも空にすると、ゲストで入る */
const isBlank = (email: string, password: string) => !email.trim() && !password;
export const authService: AuthService = {
  signIn: (email = '', password = '') => isBlank(email, password) ? authApi.guest() : authApi.login(email.trim(), password),
  // デモ用の「test / test」は、新規登録の画面から入れてもログインにする
  signUp: (email = '', password = '') => isBlank(email, password) ? authApi.guest() : email.trim().toLowerCase() === 'test' ? authApi.login('test', password) : authApi.signup(email.trim(), password),
};
