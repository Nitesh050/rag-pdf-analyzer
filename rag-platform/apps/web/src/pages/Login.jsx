import AuthLayout from "../layouts/AuthLayout";

import Card from "../components/common/Card";
import Logo from "../components/common/Logo";

import LoginForm from "../components/auth/LoginForm";

function Login() {
  return (
    <AuthLayout>

      <Card>

        <Logo />

        <LoginForm />

      </Card>

    </AuthLayout>
  );
}

export default Login;