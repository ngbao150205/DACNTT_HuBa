import { createBrowserRouter } from "react-router-dom";

import DashboardLayout from "../layouts/DashboardLayout";

import Home from "../pages/Home";
import Dashboard from "../pages/Dashboard";
import ProductAnalysis from "../pages/ProductAnalysis";
import Reviews from "../pages/Reviews";
import Issues from "../pages/Issues";
import Risk from "../pages/Risk";
import Competitor from "../pages/Competitor";


const router = createBrowserRouter([

{
    path:"/",
    element:
    <DashboardLayout>
        <Home />
    </DashboardLayout>
},


{
    path:"/dashboard",
    element:
    <DashboardLayout>
        <Dashboard />
    </DashboardLayout>
},


{
    path:"/product",
    element:
    <DashboardLayout>
        <ProductAnalysis />
    </DashboardLayout>
},


{
    path:"/reviews",
    element:
    <DashboardLayout>
        <Reviews />
    </DashboardLayout>
},


{
    path:"/issues",
    element:
    <DashboardLayout>
        <Issues />
    </DashboardLayout>
},


{
    path:"/risk",
    element:
    <DashboardLayout>
        <Risk />
    </DashboardLayout>
},


{
    path:"/competitor",
    element:
    <DashboardLayout>
        <Competitor />
    </DashboardLayout>
}


]);


export default router;