import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaEye, FaEyeSlash } from "react-icons/fa";

import Button from "../common/Button";
import Input from "../common/Input";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate("/chat");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-8 flex flex-col gap-5"
    >
      <div>
        <label className="mb-2 block text-sm text-slate-300">
          Email
        </label>

        <Input
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>

      <div>

        <label className="mb-2 block text-sm text-slate-300">
          Password
        </label>

        <div className="relative">

          <Input
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
          >
            {showPassword ? (
              <FaEyeSlash />
            ) : (
              <FaEye />
            )}
          </button>

        </div>

      </div>

      <div className="flex justify-end">

        <button
          type="button"
          className="text-sm text-cyan-400 hover:text-cyan-300"
        >
          Forgot Password?
        </button>

      </div>

      <Button type="submit">
        Login
      </Button>

      <p className="text-center text-slate-400">

        Don't have an account?

        <button
          type="button"
          className="ml-2 text-cyan-400 hover:text-cyan-300"
        >
          Register
        </button>

      </p>

    </form>
  );
}

export default LoginForm;