import {
BarChart,
Bar,
XAxis,
YAxis,
Tooltip,
ResponsiveContainer
}
from "recharts";


interface Props{

data:any[]

}



function IssueChart({data}:Props){


return (

<div
className="
bg-white
rounded-xl
shadow
p-6
"
>


<h2 className="
font-semibold
mb-5
">

Negative Issue Analysis

</h2>


<ResponsiveContainer
width="100%"
height={300}
>


<BarChart data={data}>


<XAxis
dataKey="name"
/>


<YAxis/>


<Tooltip/>


<Bar
dataKey="value"
/>


</BarChart>


</ResponsiveContainer>


</div>

)

}


export default IssueChart;