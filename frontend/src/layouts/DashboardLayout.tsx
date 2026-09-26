import type {
ReactNode
} from "react";


import Sidebar from "../components/Sidebar";
import Header from "../components/Header";


interface Props{

children:ReactNode;

}



function DashboardLayout({
children
}:Props){


return (

<div
className="
flex
min-h-screen
bg-slate-100
"
>


<Sidebar/>


<div
className="
flex-1
"
>


<Header/>


<main
className="
p-8
"
>

{children}

</main>


</div>


</div>

)


}


export default DashboardLayout;