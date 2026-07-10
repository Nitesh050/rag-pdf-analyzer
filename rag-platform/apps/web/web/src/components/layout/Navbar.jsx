import React from "react";

const Navbar = () => {
  return (
    <nav className="h-16 bg-white shadow-md flex items-center justify-between px-8">
      <h1 className="text-2xl font-bold text-blue-600">
        AI RAG Platform
      </h1>

      <div className="flex items-center gap-4">
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          Login
        </button>
      </div>
    </nav>
  );
};

export default Navbar;