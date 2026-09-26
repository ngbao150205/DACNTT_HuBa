import StatCard from "../components/StatCard";

import SentimentChart from "../components/SentimentChart";

import IssueChart from "../components/IssueChart";


import {
dashboardData
}
from "../mock/data";



function Dashboard(){



const hasData=true;



if(!hasData){

return (

<div>

<h2>
Chưa có dữ liệu phân tích
</h2>


<p>
Vui lòng nhập URL sản phẩm trước
</p>


</div>

)

}



return (

<div className="
space-y-8
">


<h1 className="
text-3xl
font-bold
">

Dashboard

</h1>



<div className="
grid
grid-cols-4
gap-6
">


<StatCard

title="Tổng review"

value={
dashboardData.totalReviews
}

/>


<StatCard

title="Tích cực"

value="75%"

/>


<StatCard

title="Tiêu cực"

value="15%"

/>


<StatCard

title="Trung lập"

value="10%"

/>


</div>



<div className="
grid
grid-cols-2
gap-6
">


<SentimentChart

data={
dashboardData.sentiment
}

/>


<IssueChart

data={
dashboardData.issues
}

/>


</div>



</div>

)

}


export default Dashboard;