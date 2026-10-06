import {
  Bell,
  Search,
} from "lucide-react";

function Header() {
  return (
    <header
      className="
        fixed
        left-72
        right-0
        top-0
        z-30
        flex
        h-20
        items-center
        justify-between
        border-b
        border-slate-200
        bg-white
        px-8
      "
    >
      <div>
        <h2
          className="
            text-xl
            font-semibold
            text-slate-900
          "
        >
          AI Customer Feedback Analysis
        </h2>

        <p
          className="
            text-sm
            text-slate-500
          "
        >
          Theo dõi phản hồi khách hàng theo thời gian thực
        </p>
      </div>

      <div
        className="
          flex
          items-center
          gap-5
        "
      >
        <div
          className="
            hidden
            items-center
            rounded-xl
            bg-slate-100
            px-4
            py-2
            md:flex
          "
        >
          <Search
            size={18}
            className="text-slate-500"
          />

          <input
            placeholder="Tìm kiếm..."
            className="
              ml-2
              w-56
              bg-transparent
              text-sm
              text-slate-700
              outline-none
              placeholder:text-slate-400
            "
          />
        </div>

        <button
          type="button"
          className="
            flex
            h-10
            w-10
            items-center
            justify-center
            rounded-full
            text-slate-500
            transition
            hover:bg-slate-100
            hover:text-slate-700
          "
        >
          <Bell size={20} />
        </button>

        <div
          className="
            flex
            h-10
            w-10
            items-center
            justify-center
            rounded-full
            bg-blue-600
            text-sm
            font-bold
            text-white
          "
        >
          A
        </div>
      </div>
    </header>
  );
}

export default Header;