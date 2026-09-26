interface Props{

title:string;

value:string | number;

}


function StatCard({
title,
value
}:Props){


return (

<div

className="
bg-white
rounded-2xl
shadow-sm
border
p-6
"

>


<p className="
text-gray-500
text-sm
">

{title}

</p>


<h2 className="
text-4xl
font-bold
mt-3
text-slate-800
">

{value}

</h2>


</div>

)

}


export default StatCard;