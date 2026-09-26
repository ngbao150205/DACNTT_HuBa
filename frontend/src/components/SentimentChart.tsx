import {
PieChart,
Pie,
Tooltip,
Legend
} from "recharts";


interface Props{

data:{
positive:number,
negative:number,
neutral:number
}

}


function SentimentChart({data}:Props){


const chartData=[

{
name:"Positive",
value:data.positive
},

{
name:"Negative",
value:data.negative
},

{
name:"Neutral",
value:data.neutral
}

]


return (

<div className="
bg-white
rounded-xl
shadow
p-6
">


<h2 className="
font-semibold
mb-5
">

Sentiment Distribution

</h2>


<PieChart width={400} height={300}>


<Pie

data={chartData}

dataKey="value"

cx="50%"

cy="50%"

outerRadius={100}

/>


<Tooltip/>

<Legend/>


</PieChart>


</div>

)

}


export default SentimentChart;