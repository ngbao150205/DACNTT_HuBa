import {
Search,
Bell
} from "lucide-react";


function Header(){

return (

<header

className="
h-20
bg-white
border-b
flex
items-center
justify-between
px-8
"

>


<div>

<h2 className="
font-semibold
text-xl
">

AI Customer Feedback Analysis

</h2>


<p className="
text-sm
text-gray-500
">

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
flex
items-center
bg-gray-100
px-4
py-2
rounded-lg
"
>


<Search size={18}/>


<input

placeholder="Tìm kiếm..."

className="
bg-transparent
outline-none
ml-2
"

/>


</div>



<Bell/>

<div
className="
w-10
h-10
rounded-full
bg-blue-600
text-white
flex
items-center
justify-center
font-bold
"
>

A

</div>



</div>


</header>

)

}


export default Header;