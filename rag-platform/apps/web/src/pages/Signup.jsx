import AuthLayout from "../layouts/AuthLayout";

import Card from "../components/common/Card";
import Logo from "../components/common/Logo";

import SignupForm from "../components/auth/SignupForm";

function Signup() {
  return (
    <AuthLayout>

      <Card>

        <Logo />

        <SignupForm />

      </Card>

    </AuthLayout>
  );
}

export default Signup;
