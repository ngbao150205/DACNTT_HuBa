import {
    Home,
    LayoutDashboard,
    Package,
    MessageSquare,
    AlertTriangle,
    ShieldAlert,
    Users
} from "lucide-react";

import {
    NavLink
} from "react-router-dom";


const menus = [

{
    name:"Trang chủ",
    path:"/",
    icon:LayoutDashboard
},

{
    name:"Dashboard",
    path:"/dashboard",
    icon:LayoutDashboard
},

{
    name:"Sản phẩm",
    path:"/product",
    icon:Package
},

{
    name:"Đánh giá khách hàng",
    path:"/reviews",
    icon:MessageSquare
},

{
    name:"Nguyên nhân tiêu cực",
    path:"/issues",
    icon:AlertTriangle
},

{
    name:"Cảnh báo rủi ro",
    path:"/risk",
    icon:ShieldAlert
},

{
    name:"Đối thủ cạnh tranh",
    path:"/competitor",
    icon:Users
}

]


function Sidebar(){

return (

<aside
className="
w-72
bg-slate-950
text-white
min-h-screen
px-5
py-6
"
>


<div className="
mb-10
">

<h1 className="
text-2xl
font-bold
">

Sentiment AI

</h1>


<p className="
text-sm
text-slate-400
mt-1
">

Customer Feedback Analytics

</p>

</div>



<nav
className="
space-y-2
"
>


{
menus.map((item)=>{

const Icon=item.icon;


return (

<NavLink

key={item.path}

to={item.path}

className={({isActive})=>

`
flex
items-center
gap-3
px-4
py-3
rounded-xl
transition

${isActive

?
"bg-blue-600 text-white"

:

"text-slate-300 hover:bg-slate-800"

}

`

}

>


<Icon size={20}/>


<span>

{item.name}

</span>


</NavLink>


)


})

}


</nav>


</aside>

)

}


export default Sidebar;