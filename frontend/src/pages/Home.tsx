import {
useState
} from "react";


import {
useNavigate
} from "react-router-dom";


function Home(){

const [url,setUrl]=useState("");

const navigate=useNavigate();


const handleAnalyze=()=>{


if(!url){

return;

}


// sau này gọi API backend ở đây


navigate("/dashboard");


}



return (

<div className="
max-w-4xl
mx-auto
mt-20
">


<h1 className="
text-4xl
font-bold
text-slate-800
">

Phân tích cảm xúc khách hàng

</h1>



<p className="
text-gray-500
mt-3
">

Nhập URL sản phẩm Tiki để hệ thống thu thập
và phân tích đánh giá khách hàng

</p>




<div className="
bg-white
shadow
rounded-2xl
p-8
mt-10
">


<input

value={url}

onChange={
(e)=>setUrl(e.target.value)
}

placeholder="
https://tiki.vn/...
"

className="
w-full
border
rounded-xl
p-4
outline-none
"

/>



<button

onClick={handleAnalyze}

className="
mt-5
bg-blue-600
text-white
px-6
py-3
rounded-xl
"

>

Bắt đầu phân tích

</button>



</div>


</div>

)

}


export default Home;