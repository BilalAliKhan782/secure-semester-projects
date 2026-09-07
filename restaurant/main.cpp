#include <stdio.h>    //header files
#include <string.h>   //string manipulation 
#include <iostream>   //filing and string manipulation
#include <fstream>    //filing read write
#include <cstdlib>
#include <chrono>
#include <thread>
#include <cctype>

using namespace std;
using std::string;
 
void Burger();        // prototype's
void Fries();
void Wings(); 
void Drinks();
void menu();
void greetings();
void writetoorderfile(const char item[], int qty, int itmtotal);
void typing_effect(const char *str);

int main();

int total=0;        //global variable
bool start_new_customer=false;
char name[10];
string filename;
	
void endorder()
{
	fstream orderfile;
	orderfile.open(filename.c_str(),ios::app);
	if(orderfile.is_open())
	{
	//printf("file is opened in append mode\n");
	orderfile<<"Your total bill is Rs. "<< total <<endl;
	}
	orderfile.close();	
	
int choice;
printf("                  Your total bill is Rs. %d",total);
printf("                  expected time 30 mins\n");

printf("                  Thank You Very Much          \n ");
printf("             +============================+          \n\n");
printf("               && Please come again && \n\n");
printf("Order for a new customer? \n");
printf("[1] yes  [2] no \n ");
scanf("%d",&choice);
if (choice==1)
{
	total = 0;
	start_new_customer = true;
	return;
}
else //(choice==2)
	 exit(0);
}

void menu()
{
char choice;
printf("                      Welcome to OPTP       \n ");
             printf("              +============================+          \n\n");
              printf("[A] Burgers\n");
                printf("*Chicken Chipotle ~ Rs.390\n");
                printf("*Swiss Beef Peparoni ~ Rs.490\n");
                printf("*Crispy Fish Fillet Burger ~ Rs.500\n");
              printf("[B] Fries\n");
                printf("*Garlic Mayo Fries ~ Rs.100\n");
                printf("*Spicy Masala Fries ~ Rs.80\n");
              printf("[C] Wings\n");
                printf("*Garlic Wings ~ Rs.500\n");
                printf("*Spicy Wings ~ Rs.480\n");
              printf("[D] Drinks\n");
                printf("*Coke 250ml ~ Rs.80\n");
                printf("*Fanta 250ml ~ Rs.80\n");
                printf("*Sprite 250ml ~ Rs.80\n");
             printf("** TRENDING ITEMS **\n");
                printf("* Chicken Chipotle Burger ~ Rs.390\n");
                printf("*Garlic Mayo Fries ~ Rs.100\n");
                printf("*Spicy Wings ~ Rs.480\n\n\n");
                
                
                  printf("Enter your choice here : ");
                  scanf(" %c", &choice);
                      {
                       if (choice== 'A' )
                        Burger();
                       else 
                       if (choice == 'B')
	                   Fries();
                       else 
	                   if (choice == 'C')
		                Wings();
	                   else 
		               if (choice == 'D')
			            Drinks();		

}

}

void writetoorderfile(const char item[], int qty, int itmtotal)
{
	fstream orderfile;
	orderfile.open(filename.c_str(),ios::app);
	if(orderfile.is_open())
 	{
 		//printf("file is opened in append mode\n");
  		orderfile<<item<<" X "<<qty<<" = "<<itmtotal<<endl;
	}
	orderfile.close();	
}

void Burger()
{
char choice;
int burtotal=0;
int quantity;
int again;
printf("BURGERS\n\n");
printf("[a]*Chicken Chipotle ~ Rs.390\n");
printf("[b]*Swiss Beef Peparoni ~ Rs.490\n");
printf("[c]*Crispy Fish Fillet Burger ~ Rs.500\n");
scanf(" %c",&choice);
	switch(choice) 
	{
		case 'a':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				burtotal=390*quantity;
				total=total+burtotal;
				char item [500]= "Chicken Chipotle ~ Rs.390";
				writetoorderfile(item, quantity, burtotal);
				break;
			}
			case 'b':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				burtotal=490*quantity;
				total=total+burtotal;
				char item [500]= "Swiss Beef Peparoni ~ Rs.490";
				writetoorderfile(item, quantity, burtotal);
				break;
			}
			case 'c':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				burtotal=500*quantity;
				total=total+burtotal;
				char item [500]= "Crispy Fish Fillet Burger ~ Rs.500";
				writetoorderfile(item, quantity, burtotal);
				break;
			}
			default:
			{
			 Burger();
			 break;
			}
	
	}
			
			printf("Do you Want Anything Else? \n[1]Yes [2]No\n ");
			scanf("%d", &again);
	
			if (again == 1 )
			{
			  menu();
			}
			else 
			{
				  endorder();	
			}
		}


void Fries()
{
	char choice;
	int fritotal;
	int quantity;
	int again;
	printf("FRIES\n\n");
	printf("[a]*Garlic Mayo Fries ~ Rs.100\n");
	printf("[b]*Spicy Masala Fries ~ Rs.80\n");
	
	scanf(" %c",&choice);
	
	switch(choice)
	{
		case 'a':
		{
			printf("Enter Quantity \n");
			scanf("%d",&quantity);
			fritotal=100*quantity;
			total=total+fritotal;
			char item [500]= "Garlic Mayo Fries ~ Rs.100";
			writetoorderfile(item, quantity, fritotal);
			break;
		}
		case 'b':
		{
			printf("Enter Quantity \n");
			scanf("%d",&quantity);
			fritotal=80*quantity;
			total=total+fritotal;
			char item [500]= "Spicy Masala Fries ~ Rs.80";
			writetoorderfile(item, quantity, fritotal);
			break;
		}
		default:
		{
			Fries();
			break;
		}	
	}
	
	printf("Do you Want Anything Else? \n[1]Yes [2]No\n ");
	scanf("%d", &again);
	
	 if (again == 1 )
		menu();
	 else 
     	endorder();

}

void Wings()
{
	char choice;
	int wintotal;
	int quantity;
	int again;
	printf("WINGS\n\n");
	printf("[a]*Garlic Wings ~ Rs.500\n");
	printf("[b]*Spicy Wings ~ Rs.480\n");
	
	scanf(" %c",&choice);
	switch(choice)
	{
		case 'a':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				wintotal=500*quantity;
				total=total+wintotal;
				char item [500]= "Garlic Wings ~ Rs.500";
				writetoorderfile(item, quantity, wintotal);
				break;			
			}
			case 'b':
				{
					printf("Enter Quantity \n");
					scanf("%d",&quantity);
					wintotal=480*quantity;
					total=total+wintotal;
					char item [500]= "Spicy Wings ~ Rs.480";
					writetoorderfile(item, quantity, wintotal);
					break;				
				}
				default:
				{
					Wings();
					break;
				}	
		}
		
		printf("Do you Want Anything Else? \n[1]Yes [2]No\n ");
		scanf("%d", &again);
		
		 if (again == 1 )
			menu();
		 else 
	     	endorder();
}

void Drinks()
{
	
	char choice;
	int dritotal;
	int quantity;
	int again;
	printf("DRINKS\n\n");
	printf("[a]*Coke 250ml ~ Rs.80\n");
	printf("[b]*Fanta 250ml ~ Rs.80\n");
	printf("[c]*Sprite 250ml ~ Rs.80\n");
	scanf(" %c",&choice);
	switch (choice)
	{
		case'a':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				dritotal=80*quantity;
				total=total+dritotal;
				char item [500]= "Coke 250ml ~ Rs.80";
				writetoorderfile(item, quantity, dritotal);
				break;					
			}
		case'b':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				dritotal=80*quantity;
				total=total+dritotal;
				char item [500]= "Fanta 250ml ~ Rs.80";
				writetoorderfile(item, quantity, dritotal);
				break;					
			}
		case'c':
			{
				printf("Enter Quantity \n");
				scanf("%d",&quantity);
				dritotal=80*quantity;
				total=total+dritotal;
				char item [500]= "Sprite 250ml ~ Rs.80";
				writetoorderfile(item, quantity, dritotal);
				break;					
			}
					default:
					{
						Drinks();
						break;
					}	
			}
			
			printf("Do you Want Anything Else? \n[1]Yes [2]No\n ");
			scanf("%d", &again);
			
			 if (again == 1 )
				menu();
			 else 
		     	endorder();
}

void greetings()
{
	char choice;
	printf(" hope you are doing well..\n");
	scanf(" %c",&choice);
	switch (choice)
	{	
		case 'N':
		case 'n': 
		{
			printf("you seem down \n..");
			printf("let me cheer you up with a joke\n");
			printf("why did the scarecrow get promoted? \n");
			printf("she was outstanding in her field :D \n");
			printf("hope you enjoyed that, i have a good sense of humor:D \n");
			break;
		}
		case 'Y':
		case 'y': 
		{ 
		  printf("Glad to hear that\n");
		  break;
		}
	}

}

void typing_effect(const char *str) {
  int i;
  for(i = 0; str[i] != '\0'; i++) {
    printf("%c", str[i]);
    fflush(stdout);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  printf("\n");
}

int main()
{
  do {
    start_new_customer = false;
    char str[] = "Welcome to the restaurant chatbot!\n";
    typing_effect(str);
	for (int i = 0; i < 10; i++) {
		printf("\rLoading [%d/%d]", i+1, 10);
		fflush(stdout);
		std::this_thread::sleep_for(std::chrono::milliseconds(100));
	}
	printf("\rLoading [10/10]\n");
	
    


	bool existingcust = false;
	
	char question;
	char regorder;
	
	printf("**_______________________________________________________  **\n");
	printf("**.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.*.**\n");
	printf("**'''''''''''''''''''''''''''''''''''''''''''''''''''''''''**\n");
	printf("**|||||||||||||||||||||||||||||||||||||||||||||||||||||||||**\n");
	printf("____________________________________________________________ \n");
	printf("**                                                         **\n\n");

	printf("OPTP Online Ordering System\n");
	printf("please Enter Your Name \n");
	scanf("%9s", name);
	for (char &character : name) {
		if (character == '\0') break;
		if (!std::isalnum(static_cast<unsigned char>(character)) && character != '_' && character != '-') {
			character = '_';
		}
	}

	filename = std::string("") + name + ".txt";
	
	fstream custfile;
	custfile.open("custfile.txt", ios::in);
 	char ch[10];
 	if(custfile.is_open())
 	{
 		//printf("File is opened\n");
 		while (!custfile.eof())
		{
			custfile>>ch;
			if( strcmp(name, ch)==0)
			{
				existingcust = true;
				break;
			}
		}
		custfile.close();
	}	
	
	if(existingcust)
	{		
		printf("Welcome Back  ");
		printf("%s", name);
		
		greetings();
				
		printf("\nShould I place your regular order ?\n");
		scanf(" %c",&regorder);
	
		switch (regorder)
		{
			case 'Y':
			case 'y': 
			{
				printf("\n Okay Sir ordering your usual preference \n");
				printf("Your usual order :\n");
	
				// to be replaced with order file
				fstream reorderfile;
				reorderfile.open(filename.c_str(),ios::in);
				char ch[5000];
				string tmp;
				reorderfile>>ch;
				while(std::getline(reorderfile,tmp, '\n'))
				{
					printf("                  ");
					printf("%s", tmp.c_str());
					printf("\n");
				}
				reorderfile.close();
				// end of reading order file
				endorder();
				break;
			}
		case 'N':
		case 'n': 
			 {						
				printf("Great decision, we have new items added in our menu recently\n");
				printf("Showing you Our menu and specials that are trending these days\n\n");
				
				fstream neworder;
				neworder.open(filename.c_str(), ios::out);
				neworder.close();
				break;	
			}
		}
		printf(" Showing you Our menu and specials that are trending these days\n");
	
		menu();		
	}	
	else
	{
		// new customer
		printf("Welcome to OPTP ");
		printf("%s ",name);
		
		fstream custfile;
		custfile.open("custfile.txt",ios::app);
		custfile<<name;
		custfile<<"\n";	
		custfile.close();
			
		greetings();
		
		printf("wondering who am I? \n");
		scanf(" %c",&question);
		
		switch (question)
		{
			case 'Y':
			case 'y':
				{
					printf("\n great, let me introduce myself \n");
					printf("My name is Chatoo, I am a chatbot, and i will be assisting you in oredering best food from our restaurant. \n");
					printf("Hope you enjoy working with a bot. Don''t worry i am designed to be quick, efficient and interactive just like a regular waiter \n");
					break;					
				}
 
			case 'N':
			case 'n':
				{
					printf("great\n");
					printf("Glad to see your acceptance towards me :) \n");
					break;					
				}
					
		}
		
		printf("Hope you are ready to order \n");
		printf(" Showing you Our menu and specials that are trending these days\n");
	
		menu();
	}
	
	} while (start_new_customer);
	return 0;
}
