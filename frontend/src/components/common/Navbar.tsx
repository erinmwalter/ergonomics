import React from 'react';
import { Navbar, NavbarBrand, Nav, NavItem, NavLink } from 'reactstrap';

const AppNavbar: React.FC = () => {
  return (
    <Navbar color="dark" dark expand="md">
      <NavbarBrand href="/">Process Adherence Monitoring System</NavbarBrand>
      <Nav className="ms-auto" navbar>
         <NavItem>
          <NavLink href="/"  style={{color:"white"}}>Home</NavLink>
        </NavItem>
        <NavItem>
          <NavLink href="/config" style={{color:"white"}}>Configuration</NavLink>
        </NavItem>
        <NavItem>
          <NavLink href="/process" style={{color:"white"}}>Processes</NavLink>
        </NavItem>
         <NavItem>
          <NavLink href="/analysis" style={{color:"white"}}>Analysis</NavLink>
        </NavItem>
      </Nav>
    </Navbar>
  );
};

export default AppNavbar;