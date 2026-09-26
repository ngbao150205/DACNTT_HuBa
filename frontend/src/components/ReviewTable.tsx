interface Props{

reviews:any[]

}


function ReviewTable({reviews}:Props){


return (

<div
className="
bg-white
rounded-xl
shadow
p-6
"
>


<h2 className="font-semibold mb-4">

Recent Negative Reviews

</h2>



<table
className="
w-full
"
>


<thead>

<tr>

<th>
Review
</th>

<th>
Issue
</th>

<th>
Status
</th>

</tr>

</thead>



<tbody>


{
reviews.map(
(item,index)=>(

<tr key={index}
className="border-t"
>

<td className="p-3">

{item.content}

</td>


<td>

{item.issue}

</td>


<td>

<span
className="
text-red-500
"
>

Negative

</span>

</td>


</tr>

)

)

}


</tbody>


</table>


</div>

)

}


export default ReviewTable;